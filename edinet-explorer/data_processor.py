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

class Period:
    def __init__(self, api_key: str, start_date: datetime.date, end_date: datetime.date, json_path = False) -> None:
        self.get_basics(api_key, start_date, end_date, json_path)

    def get_basics(self, api_key,start_date, end_date,json_path):
        if json_path:
            with open(json_path,"r") as f:
                self.json = json.load(f)
            self.info_url = self.json["info_url"]
            self.doc_url = self.json["doc_url"]
            self.dates = self.json["dates"]
            self.results = self.json["results"]
            self.start_date = datetime.datetime.strptime(self.dates[0],'%Y/%m/%d')
            self.end_date = datetime.datetime.strptime(self.dates[-1],'%Y/%m/%d')
            self.days = int((self.end_date - self.start_date).days)

        else:
            self.info_url = "https://api.edinet-fsa.go.jp/api/v2/documents.json"
            self.doc_url = "https://api.edinet-fsa.go.jp/api/v2/documents/"
            self.start_date = start_date
            self.end_date = end_date
            self.days = int((self.end_date - self.start_date).days)
            self.dates =  [datetime.datetime.strftime(start_date + datetime.timedelta(days), '%Y/%m/%d') for days in range(self.days)]
            self.api_key = api_key
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
    
    def get_documents(self, folder:str, show_progress = False):
        count = 0
        folder += "/xbrl_csv"
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.makedirs(f"{folder}/_zip_dir")
        for key in self.results.keys():
            my_zip = f"{folder}/_zip_dir/{key}.zip"
            params = {"type": 5, "Subscription-Key": self.api_key }
            res = requests.get(f"{self.doc_url}{key}", params = params) 
            sleep(0.2)
            with open(my_zip, "wb") as file:
                for chunk in res.iter_content(chunk_size = 1024):
                    file.write(chunk)

            with zipfile.ZipFile(my_zip) as zip_file:
                for member in zip_file.namelist():
                    filename = os.path.basename(member)
                    # only keep audit report
                    identifier = filename.split("-")[1]    
                    if identifier == "aai":
                        # skip directories
                        if not filename:
                            continue
                        # copy file (taken from zipfile's extract)
                        csv_dir = os.path.join(folder, filename)
                        source = zip_file.open(member)
                        target = open(csv_dir, "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                        # add csv_dir to self attributes here
                        self.results[key]["audit_csv"] = csv_dir
                        break
                    else:
                        self.results[key]["audit_csv"] = ""

                for member in zip_file.namelist():
                    filename = os.path.basename(member)
                    # only keep audit report
                    identifier = filename.split("-")[1]    
                    if identifier == "asr":
                        # skip directories
                        if not filename:
                            continue
                        # copy file (taken from zipfile's extract)
                        csv_dir = os.path.join(folder, filename)
                        source = zip_file.open(member)
                        target = open(csv_dir, "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                        # add csv_dir to self attributes here
                        self.results[key]["annual_csv"] = csv_dir
                        break
                    else:
                        self.results[key]["annual_csv"] = ""
        
            count += 1
            if show_progress: yield count
            os.remove(my_zip)
        shutil.rmtree(f"{folder}/_zip_dir")
        
    def save_json(self, folder:str):
        self.json = {
            "info_url": self.info_url,
            "doc_url": self.doc_url,
            "dates": self.dates,
            "results": self.results
        }

        json_dir  = f"{folder}/period.json"
        with open(json_dir, "w") as f:
            json.dump(self.results, f)

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
