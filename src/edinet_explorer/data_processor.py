from time import sleep
import  os
import  datetime
import requests
import shutil
import zipfile
import re
import csv
import json
import pandas as pd
from typing import Literal
from jtext import JText
from collections import Counter
from tqdm import tqdm

class Period:
    def __init__(self, api_key = None, start_date = None, end_date = None, json_path = None) -> None:
        self.info_url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
        self.doc_url = "https://api.edinet-fsa.go.jp/api/v2/documents/"

        if json_path is not None:
            self._init_from_json(json_path)
        elif api_key is not None and start_date is not None and end_date is not None:
            self._get_basics(api_key, start_date, end_date)
        
        else:
            raise ValueError("Please enter api_key, start_date, end_date or json_path")

    def _init_from_json(self,json_path):
        if os.path.exists(json_path) == False:
            raise ValueError("can not find json file")
        else:
            with open(json_path,"r") as f:
                self.json = json.load(f)
            self.dates = self.json["dates"]
            self.results = self.json["results"]
            self.start_date = datetime.datetime.strptime(self.dates[0],'%Y/%m/%d')
            self.end_date = datetime.datetime.strptime(self.dates[-1],'%Y/%m/%d')
            self.days = int((self.end_date - self.start_date).days)
            self.results_df = self._convert_to_dataframe()


    def _get_basics(self, api_key,start_date, end_date):
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date
        self.days = int((self.end_date - self.start_date).days)
        self.dates =  [datetime.datetime.strftime(start_date + datetime.timedelta(days), '%Y/%m/%d') for days in range(self.days)]
        self.results = dict()

    def get_results(self, show_progress = False):
        count = 1
        for date in self.dates:
            count += 1
            params = {"date": datetime.datetime.strptime(date,"%Y/%m/%d").date(), "type": 2, "Subscription-Key": self.api_key}
            for i in range(3):
                try:
                    res = requests.get(url = self.info_url,params = params)
                except:
                    sleep(2)
                else:
                    if res.status_code == 200: break
            res_json = res.json()
            if res_json["metadata"]["status"] == "200":
                for firm in res_json["results"]: 
                    if (firm['docTypeCode'] == "120") & (firm['secCode'] != None) & (firm["xbrlFlag"] == "1") & (firm["csvFlag"] == "1"):
                        self.results[firm["docID"]] = {key:firm[key] for key in ('docID','secCode','filerName','periodStart','periodEnd','docDescription')}
                        self.results[firm["docID"]]["date"] = date
                    else: pass
            else: pass
            if show_progress: 
                yield count
            else: pass
        self.results_df = self._convert_to_dataframe()
    
    @staticmethod
    def search_file(my_zip, folder, file_type: Literal["audit_csv", "annual_csv", "audit_xbrl", "annual_xbrl"]) -> str:
        name_dic = {"audit_csv": "aai", "annual_csv": "asr", "audit_xbrl": "aai", "annual_xbrl": "asr"}
        type_dic = {"audit_csv": ".csv", "annual_csv": ".csv", "audit_xbrl": ".xbrl", "annual_xbrl": ".xbrl"}
        file_dir = ""

        with zipfile.ZipFile(my_zip) as zip_file:
            for member in zip_file.namelist():
                filename = os.path.basename(member)
                if filename.endswith(type_dic[file_type]):
                    identifier = filename.split("-")[1]    
                    if identifier == name_dic[file_type]:       # only keep target report
                        if not filename:                        # skip directories
                            continue
                        file_dir = os.path.join(folder, filename)        # copy file (taken from zipfile's extract)
                        source = zip_file.open(member)
                        target = open(file_dir, "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                    else:
                        pass
                else:
                    pass
        return file_dir

    def api_download(self, key, folder, ref_num: int) -> None:
        sleep(0.2)
        if ref_num not in [1,2,5]:
            return None
        else:
            params = {"type": ref_num, "Subscription-Key": self.api_key}
            res = requests.get(f"{self.doc_url}{key}", params = params) 

            if ref_num in [1,5]:
                my_file = f"{folder}/_zip_dir/{key}.zip"
            elif ref_num == 2:
                my_file = f"{folder}/data/pdf/{key}.pdf"
            else: pass

            if res.status_code == 200:
                with open(my_file, "wb") as file:
                    for chunk in res.iter_content(chunk_size = 1024):
                        file.write(chunk)
                return my_file
            else:
                return None

    @staticmethod
    def check_make(*args):
        for arg in args:
            if not os.path.exists(arg):
                os.makedirs(arg)
            else:
                pass

    def get_documents(self, folder:str, show_progress = False, **kwargs):
        count = 0
        # Create data root path
        data_folder = os.path.join(folder, "data")
        tempo_file = os.path.join(folder, "_zip_dir")
        self.check_make(data_folder,tempo_file)

        # Assign folder paths
        if kwargs.get("csv", False) == True:
            audit_csv_folder = os.path.join(data_folder, "audit_csv")
            annual_csv_folder = os.path.join(data_folder, "annual_csv")
            self.check_make(audit_csv_folder, annual_csv_folder)
        else:
            pass

        if kwargs.get("xbrl", False) == True:
            audit_xbrl_folder = os.path.join(data_folder, "audit_xbrl")
            annual_xbrl_folder = os.path.join(data_folder, "annual_xbrl")
            self.check_make(audit_xbrl_folder, annual_xbrl_folder)
        else:
            pass

        if kwargs.get("pdf", False) == True:
            pdf_folder = os.path.join(data_folder, "pdf")
            self.check_make(pdf_folder)
        else:
            pass

        for key in self.results.keys():
            result_dict = {"xbrl": 1, "pdf": 2, "csv": 5}

            if kwargs.get("xbrl", False) == True:
                xbrl_zip = self.api_download(key, folder, result_dict["xbrl"])
                self.results[key]["audit_xbrl"] = self.search_file(xbrl_zip, folder = audit_xbrl_folder, file_type = "audit_xbrl")
                self.results[key]["annual_xbrl"] = self.search_file(xbrl_zip, folder = annual_xbrl_folder, file_type = "annual_xbrl")
                os.remove(xbrl_zip)
            else: 
                pass

            if kwargs.get("csv", False) == True:
                csv_zip = self.api_download(key, folder, result_dict["csv"])
                self.results[key]["audit_csv"] = self.search_file(csv_zip, folder = audit_csv_folder, file_type = "audit_csv")
                self.results[key]["annual_csv"] = self.search_file(csv_zip, folder = annual_csv_folder, file_type = "annual_csv")
                os.remove(csv_zip)
            else: 
                pass

            if kwargs.get("pdf", False) == True:
                self.results[key]["pdf"] = self.api_download(key, folder, result_dict["pdf"])
            else:
                pass

            count += 1
            if show_progress: yield count
        shutil.rmtree(f"{folder}/_zip_dir")
        
    def get_auditors(self):
        result_dict = {}
        for key in self.results.keys():
            sub_dict = {}
            csv_path = self.results[key]["audit_csv"]
            if csv_path:
                with open(csv_path, mode='r', newline='', encoding='utf_16',errors='ignore') as file:
                    reader = csv.reader(file)
                    header = next(reader)  
                    value = next(reader)[0].split("\t")[-1]     # Get the last cell's value of the first row
                    value = re.sub(r"\s+", '', value)
                    end_chars = ["当監査法人は", "＜財務諸表監査＞", "監査意見","＜連結財務諸表監査＞"]
                    for char in end_chars:
                        if value.find(char) != -1:
                            sub_str = value.partition(char)[0]
                            value = sub_str
                        else: pass
                    start_chars = ["御中","平成"]
                    for char in start_chars:
                        if value.find(char) != -1:
                            sub_str = value.partition(char)[2]
                            value = sub_str
                        else: pass
                    sub_strs = [r'\d{4}年\d{1}月\d{2}日',r'\d{4}年\d{2}月\d{2}日', r'\d{2}年\d{1}月\d{2}日',r'\d{2}年\d{2}月\d{2}日',  
                                "代表社員", "業務執行社員","指定有限責任社員","指定社員","公認会計士",
                                "印", "㊞"]
                    for sub in sub_strs:
                        value = re.sub(sub, " ", value)
                    value = value.lstrip(' ')
                raw_list = value.split(" ")
                auditor_list = [auditor for auditor in raw_list if auditor]
                if "監査法人" in auditor_list[0]:
                    sub_dict["Auditor"] = auditor_list[0]
                    sub_dict["Lead EP"] = auditor_list[1]
                    seq = 1
                    for EP in auditor_list[2:]:
                        sub_dict[f"Vice EP {seq}"] = EP
                        seq += 1
                else: pass
                result_dict[key] = sub_dict
        return result_dict

    def get_numeric(self, type: str = "separate" ):
        type_dict = {"consolidated": "連結", "separate": "個別","consolidated":"consolidated", "個別":  "個別"}
        result_dict = {}
        for key in self.results.keys():
            sub_dict = {}
            csv_path = self.results[key]["annual_csv"]
            if csv_path:
                df_numeric = pd.read_csv(csv_path,encoding='utf-16',on_bad_lines='skip', sep = "\t") # sep makes sure pandas does not read all line as a string
                df_numeric = df_numeric.loc[df_numeric["値"].str.isdigit()]
                df_numeric = df_numeric.loc[df_numeric['相対年度'].isin(["当期","当期末"])]
                df_numeric = df_numeric.loc[df_numeric['連結・個別'] == type_dict[type]]
                df_numeric = df_numeric.drop_duplicates(subset = "項目名")
                df_numeric = df_numeric[["項目名","値"]]
                for index, row in df_numeric.iterrows():
                    sub_dict[row["項目名"]] = int(row["値"])
                result_dict[key] = sub_dict
        return result_dict
    
    # convert self.results from dictionary to a DataFrame
    def _convert_to_dataframe(self) -> pd.DataFrame:
        convert_dict = {}
        check_keys = True
        # check if the results dicts have the same keys
        first_dict_keys = set(next(iter(self.results.values())).keys())
        for sub_dict in self.results.values():
            if set(sub_dict.keys()) != first_dict_keys:
                check_keys = False

        # convert to dataframe if it has the same keys
        if check_keys == True:
            for key in first_dict_keys:
                convert_dict[key] = []
            for sub_dict in self.results.values():
                for key in sub_dict.keys():
                    convert_dict[key].append(sub_dict[key])
        results_df = pd.DataFrame(convert_dict)
        results_df[["year","month","day"]] = results_df['periodEnd'].str.split("-", expand=True).astype(int)

        results_df = results_df.drop_duplicates(subset=['secCode', 'year'])
        results_df = results_df.sort_values(by=['secCode', 'year']).reset_index(drop=True)

        return results_df

    def get_textual(self, items: dict = {"Textual Data":True}):
        result_dict = {}
        for key in self.results.keys():
            sub_dict = {}
            csv_path = self.results[key]["annual_csv"]
            if csv_path:
                df_textual = pd.read_csv(csv_path,encoding='utf-16',on_bad_lines='skip', sep = "\t") # sep makes sure pandas does not read all line as a string
                df_textual = df_textual.loc[-df_textual["値"].str.isdigit()]
                df_textual = df_textual.loc[df_textual['要素ID'].str.contains("TextBlock")]
                df_textual = df_textual.drop_duplicates(subset = "項目名")

                if items.get("Textual Data") == False:
                    id_ref = {"MD&A": ["jpcrp_cor:ManagementAnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock", 
                                       "jpcrp_cor:AnalysisOfFinancialPositionOperatingResultsAndCashFlowsTextBlock"],
                                      "Risks": ["jpcrp_cor:BusinessRisksTextBlock"],
                                      "CG": ["jpcrp_cor:OverviewOfCorporateGovernanceTextBlock", "jpcrp_cor:ExplanationAboutCorporateGovernanceTextBlock"]}
                    select_id = {key:id_ref[key] for key in id_ref if items.get(key) == True}
                    select_column = [item for sublist in select_id.values() for item in sublist]
                    df_textual = df_textual.loc[df_textual['要素ID'].isin(select_column)]
                else: pass

                df_textual = df_textual[["項目名","値"]]
                for index, row in df_textual.iterrows():
                    sub_dict[row["項目名"]] = re.sub(r"[\u3000 \t]", "", row["値"])
                
                result_dict[key] = sub_dict


            else: pass
        return result_dict
 
    # Note: does not apply to gui yet; lack of dividision of each year (important)
    def get_boilerplate(self, words_per_phrase: int = 8, bottom_percent: int = 30, top_percent:int = 80) -> pd.DataFrame:
        df = self.results_df.copy()                            # this is what returns at last
        year_group = df.groupby("year")
        result_dict = {}                                        # this is the new column
        for year in year_group.groups.keys():
            print(f"Dealing with data in {year}")
            total_dict = {}                                     # a dict with document ID as key and Counter of n-gram as value
            boiler_counter = Counter()                          # a empty Counter that takes boilerplate n-gram as key and the number of file that n-gram appears as value
            
            for index in tqdm(year_group.groups[year]):
                csv_path = df.iloc[index]["annual_csv"]
                if csv_path:
                    try:
                        # feed the csv path to JText instance and get the list of n-gram
                        sub_jtext = JText(csv_path)
                        sub_ngram = sub_jtext.get_ngram(words_per_phrase)           # n-gram list
                        sub_counter = Counter(sub_ngram)                            # a Counter for each file that takes n-gram as key and frequency as value
                    except:
                        sub_counter = Counter()                                     # set an empty Counter if errors occur

                    finally:
                        total_dict[index] = sub_counter
                        sub_unique = sub_counter.copy()
                        for n_gram in sub_unique:
                            sub_unique[n_gram] = 1
                        boiler_counter.update(sub_unique)
                else:
                    total_dict[index] = Counter()                                              # set an empty Counter if there is no csv file
            bottom_number = round(len(year_group.groups[year])*bottom_percent/100)             # total numbers of files * bottom-line ratio
            top_number = round(len(year_group.groups[year])*top_percent/100)

            for n_gram in list(boiler_counter.keys()):
                if boiler_counter[n_gram] <= bottom_number:
                    del boiler_counter[n_gram]                                              # the n-gram is not boiler-plate if it is below the bottom-line number
                elif boiler_counter[n_gram] >= top_number:
                    del boiler_counter[n_gram]                                              # the n-gram is not boiler-plate if it is above the top-line number
                else:
                    pass
            
            # loop the whole record again
            for key in total_dict.keys():
                sub_counter = total_dict[key]
                total_number = sub_counter.total()
                boiler_number = 0 

                for n_gram in sub_counter:
                    if n_gram in boiler_counter:
                        boiler_number += sub_counter[n_gram]                        # count the occurrence only when it is in the boilerplate n-gram list 
                    else:
                        pass

                try:
                    boiler_ratio = boiler_number/total_number
                except:
                    boiler_ratio = 0
                finally:
                    result_dict[key] = boiler_ratio

        boiler_series = pd.Series(result_dict)
        df["boiler"] = boiler_series

        return df

    def get_stickiness(self, words_per_phrase: int = 8) ->pd.DataFrame:
        sticky_list = [0,]
        df = self.results_df.copy()
        for i in tqdm(range(1, len(self.results_df))):
            current_row = self.results_df.iloc[i]
            previous_row = self.results_df.iloc[i - 1]
            if current_row['secCode'] == previous_row['secCode'] and current_row['year'] == previous_row['year'] + 1:
                try:
                    current_n_gram = Counter(JText(current_row["annual_csv"]).get_ngram(words_per_phrase))
                    previous_n_gram = Counter(JText(previous_row["annual_csv"]).get_ngram(words_per_phrase))
                    total = current_n_gram.total()
                    count = 0
                    for n_gram in current_n_gram.keys():
                        if n_gram in previous_n_gram:
                            count += current_n_gram[n_gram]
                        else:
                            pass
                    sticky_ratio = count/total
                except:
                    sticky_ratio = 0
            else:
                sticky_ratio = 0
            sticky_list.append(sticky_ratio)

        df["stickiness"] = sticky_list
        
        return df

    def save_json(self, folder:str):
        self.json = {
            "dates": self.dates,
            "results": self.results
        }

        json_dir  = os.path.join(folder, "period.json")
        
        with open(json_dir, "w") as f:
            json.dump(self.json, f)

