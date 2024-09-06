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

    def save_json(self, folder:str):
        self.json = {
            "dates": self.dates,
            "results": self.results
        }

        json_dir  = os.path.join(folder, "period.json")
        
        with open(json_dir, "w") as f:
            json.dump(self.json, f)

