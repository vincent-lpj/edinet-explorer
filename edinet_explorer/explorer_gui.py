from data_processor import Period
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from PIL import Image
from CTkMessagebox import CTkMessagebox
import pandas as pd
from copy import deepcopy
import datetime
import requests
import os

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.set_root()
        self.set_upperframe()
        self.set_underframe()
    
    # Set up root window
    def set_root(self):
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width - 1000) // 2
        y = (screen_height - height - 600) // 2
        self.geometry(f"1000x600+{x}+{y}")
        self.title("EDINET Explorer")
        self.resizable(False, False)
        self.bind("<Escape>", lambda event: self.quit())
        win_icon_path = os.path.join(os.getcwd(), "edinet_explorer/resources/icons/icon_win.ico") # Add icon using relative path
        self.iconbitmap(win_icon_path)

        self.label_font = ctk.CTkFont(family="Roboto", size = 15)
    
    # Add widget to app
    def set_upperframe(self):
        self.upper = ctk.CTkFrame(self, fg_color = "#e1edf0")
        self.upper.place(rely = 0, relx = 0, relwidth = 1, relheight = 0.25, anchor = "nw")

        # Left Frame
        ctk.CTkFrame(self.upper, fg_color = "transparent").place(rely = 0, relx = 0, relwidth = 0.1, relheight = 1, anchor = "nw")

        # Middle Frame
        self.uppermiddle = ctk.CTkFrame(self.upper, fg_color = "transparent")
        self.uppermiddle.place(rely = 0, relx = 0.1, relwidth = 0.6, relheight = 1, anchor = "nw")
        self.set_fileinfo()
        self.set_dateinfo()
        self.set_keyinfo()

        # Right Frame
        self.upperright = ctk.CTkFrame(self.upper, fg_color = "transparent")
        self.upperright.place(rely = 0, relx = 0.8, relwidth = 0.2, relheight = 1, anchor = "nw")
        self.set_download_parse()
    
    def set_underframe(self):
        self.under = ctk.CTkFrame(self, fg_color = "#dbe0eb")
        self.under.place(rely = 0.25, relx = 0, relwidth = 1, relheight = 0.75, anchor = "nw")
    
    def file_to_entry(self):
        filename = ctk.filedialog.askdirectory()
        self.folder_selector.insert(ctk.END, filename)
        self.folder_selector.configure(state = "disabled")
    
    def set_fileinfo(self):
        file_frame = ctk.CTkFrame(self.uppermiddle, fg_color = "transparent")
        file_frame.place(relx = 0, rely = 0, relwidth = 1, relheight = 0.5, anchor = "nw")

        ctk.CTkLabel(file_frame,
                     text = "Please select your folder here:", font = self.label_font).pack(anchor = "w", pady = 5)

        # Get Directory from File Explorer
        self.folder_selector = ctk.CTkEntry(file_frame, width = 550)
        file_icon_path = os.path.join(os.getcwd(), "edinet_explorer/resources/icons/folder.png")    # Add icon using relative path
        file_icon = ctk.CTkImage(Image.open(file_icon_path), size=(20, 20))
        folder_selector_button = ctk.CTkButton(file_frame, fg_color = '#dbe0eb', 
                                               image = file_icon, 
                                               text = "", 
                                               command = self.file_to_entry, 
                                               width = 30)
        self.folder_selector.pack(side = "left")
        folder_selector_button.pack(side = "left",padx = 2)
    
    def set_keyinfo(self):
        key_frame = ctk.CTkFrame(self.uppermiddle, fg_color = "transparent")
        key_frame.place(relx = 0, rely = 0.5, relwidth = 0.5, relheight = 0.5, anchor = "nw")

        # Get API Keys
        key_info = ctk.CTkLabel(key_frame,
                                text = "Please enter your API Key:",font = self.label_font )
        key_info.pack(anchor = "w")

        self.api_key = ctk.StringVar()
        key_entry = ctk.CTkEntry(key_frame, show = "*", textvariable = self.api_key, width = 170)
        try:
            key_entry.insert( ctk.END, os.environ["edinet_key"])
        except: pass
        key_entry.pack(anchor = "w", side = "left")
        def show_key():
            if key_check.get() == 1: key_entry.configure(show = "")
            else: key_entry.configure(show = "*")
        key_check = ctk.CTkCheckBox(key_frame, command = show_key, text = "Show Key", checkbox_width = 18, checkbox_height=18)
        key_check.pack(anchor = "w", side = "left", padx = 20)
    
    def set_dateinfo(self):
        date_frame = ctk.CTkFrame(self.uppermiddle, fg_color = "transparent")
        date_frame.place(relx = 0.5, rely = 0.5, relwidth = 0.5, relheight = 0.5, anchor = "nw")

        start_frame = ctk.CTkFrame(date_frame, fg_color = "transparent")
        start_frame.place(relx = 0, rely = 0, relwidth = 0.5, relheight = 1, anchor = "nw")
        ctk.CTkLabel(start_frame, 
                     text = "From:",font = self.label_font).pack(anchor = "nw", expand = True)
        self.start_entry = ctk.CTkEntry(start_frame, placeholder_text = "YYYY/MM/DD" )
        self.start_entry.pack(anchor = "nw", expand = True)

        end_frame = ctk.CTkFrame(date_frame, fg_color = "transparent")
        end_frame.place(relx = 0.5, rely = 0, relwidth = 0.5, relheight = 1, anchor = "nw")
        ctk.CTkLabel(end_frame, 
                     text = "To:", font = self.label_font).pack(anchor = "nw", expand = True)
        self.end_entry = ctk.CTkEntry(end_frame,placeholder_text = "YYYY/MM/DD")
        self.end_entry.pack(anchor = "nw", expand = True)
    
    def check_info(self):
        # check if date is valid
        try:
            start = datetime.datetime.strptime(self.start_entry.get(), '%Y/%m/%d')
            end = datetime.datetime.strptime(self.end_entry.get(), '%Y/%m/%d')
        except ValueError:
            return False
        else:
            if (end- start).days < 0:
                return False

        # check api key
        try:
            params = {"date":  datetime.datetime.strptime(self.start_entry.get(), '%Y/%m/%d'),
                       "type": 2, 
                       "Subscription-Key": self.api_key.get()}
            res = requests.get("https://api.edinet-fsa.go.jp/api/v2/documents.json", params = params)
        except: 
            return False
        else:
            if not res.status_code == 200:
                print(res.status_code)
                return False
            else:
                return True
        
    def download(self):
        # Return if there is invalid input
        if not self.check_info():
            CTkMessagebox(title = "Error",
                          fg_color = "transparent",
                          message= "Please check your input",
                          icon="warning",
                          option_1 = "OK")
            return
        self.period = Period(start_date = datetime.date(*map(int, self.start_entry.get().split('/'))), 
                        end_date = datetime.date(*map(int, self.end_entry.get().split('/'))), 
                        api_key = self.api_key.get())
        
        info_win = ctk.CTkToplevel(self, fg_color = "#F0F0F0")
        width = info_win.winfo_width()
        height = info_win.winfo_height()
        screen_width = info_win.winfo_screenwidth()
        screen_height = info_win.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        info_win.title("Searching")
        info_win.geometry(f"400x150+{x}+{y}")
        info_win.resizable(False, False)
        info_win.attributes('-topmost',True)

        progress_frame = ctk.CTkFrame(info_win, fg_color="#F0F0F0",width=300, height = 12)
        text_frame = ctk.CTkFrame(info_win, fg_color="#F0F0F0",width=300, height = 30)

        progress_count = ctk.StringVar()
        ctk.CTkLabel(text_frame , text_color = "#4B41DE", 
                     textvariable = progress_count, 
                     font = ctk.CTkFont(family="Arial",size = 20, weight="bold") ).place(relx = 0.025,rely = 1, anchor = "sw")
        ctk.CTkLabel(text_frame , text = "Your Progress", text_color = "#BDBDBD").place(relx = 0.965,rely = 1, anchor = "se")
        
        info_progress = ctk.CTkProgressBar(progress_frame , 
                                      width=300, height = 12,
                                      orientation="horizontal",corner_radius = 90,
                                      fg_color = "#D6D6D6",progress_color="#4B41DE",
                                      mode="determinate")
        info_progress.pack()
        info_progress.set(0)

        text_frame.place(relx = 0.1,rely = 0.3, relwidth = 0.8)
        progress_frame.place(relx = 0.1,rely = 0.5, relwidth = 0.8)

        total_len = len(self.period.dates)
        for count in self.period.get_results(show_progress=True):
            progress_str = f"{count}/{total_len}"
            progress_count.set(progress_str)
            info_progress.set(count/total_len)
            info_progress.update()

        info_win.destroy()

        try:
            self.treeview.destroy()
        except AttributeError: 
            self.set_treeview()
        else: self.set_treeview()


        message = CTkMessagebox(title="Continue?", 
                        fg_color = "transparent",
                        message= f"{len(self.period.results.keys())} annual reports are found,\nDo you want to continue download?",
                        icon="check", 
                        option_1="No", 
                        option_2="Yes")
        
        if message.get() == "Yes":
            try:
                info_win = ctk.CTkToplevel(self, fg_color = "#F0F0F0")
                width = info_win.winfo_width()
                height = info_win.winfo_height()
                screen_width = info_win.winfo_screenwidth()
                screen_height = info_win.winfo_screenheight()
                x = (screen_width - width) // 2
                y = (screen_height - height) // 2
                info_win.title("Downloading")
                info_win.geometry(f"400x150+{x}+{y}")
                info_win.resizable(False, False)
                info_win.attributes('-topmost',True)

                progress_frame = ctk.CTkFrame(info_win, fg_color="#F0F0F0",width=300, height = 12)
                text_frame = ctk.CTkFrame(info_win, fg_color="#F0F0F0",width=300, height = 30)

                progress_count = ctk.StringVar()
                ctk.CTkLabel(text_frame , text_color = "#4B41DE", 
                            textvariable = progress_count, 
                            font = ctk.CTkFont(family="Arial",size = 20, weight="bold") ).place(relx = 0.025,rely = 1, anchor = "sw")
                ctk.CTkLabel(text_frame , text = "Your Progress", text_color = "#BDBDBD").place(relx = 0.965,rely = 1, anchor = "se")
                
                info_progress = ctk.CTkProgressBar(progress_frame , 
                                            width=300, height = 12,
                                            orientation="horizontal",corner_radius = 90,
                                            fg_color = "#D6D6D6",progress_color="#4B41DE",
                                            mode="determinate")
                info_progress.pack()
                info_progress.set(0)

                text_frame.place(relx = 0.1,rely = 0.3, relwidth = 0.8)
                progress_frame.place(relx = 0.1,rely = 0.5, relwidth = 0.8)

                total_len = len(self.period.results.keys())
                for count in self.period.get_documents(folder = self.folder_selector.get(), show_progress =True):
                    progress_str = f"{count}/{total_len}"
                    progress_count.set(progress_str)
                    info_progress.set(count/total_len)
                    info_progress.update()

                info_win.destroy()          # Destroy progressbar window after finishing
            
            except:
                CTkMessagebox(title = "Error",
                          fg_color = "transparent",
                          message= "Something wrong with download",
                          icon="warning",
                          option_1 = "OK")      # Show error message 
            else:
                CTkMessagebox(title = "Succeed",
                          fg_color = "transparent",
                          message= "Download Succeed!",
                          icon="check",
                          option_1 = "OK")      # Show success message 
                self.parse_button.configure(state = "normal") # Enable parse button only when download succeed 
                self.period.save_json(folder = self.folder_selector.get())
        else:
            return

    # Set the buttons for download and parse
    def set_download_parse(self):
        download_button = ctk.CTkButton(self.upperright , fg_color = "#00a0a0", 
                                        text = "Download", font = ctk.CTkFont(family = "Arial",weight = "bold"),
                                        command = self.download)
        download_button.pack(expand = True)

        self.parse_button = ctk.CTkButton(self.upperright , fg_color = "#00a0a0", 
                                          text = "Parse", font = ctk.CTkFont(family = "Arial",weight = "bold"), 
                                          command = self.select_parse, state = "disabled")
        self.parse_button.pack(expand = True)
    
    def set_treeview(self):
        # datas for treeview
        columns=("Index","Date","docID","secCode","filerName", "docDescription")

        # treeview
        self.treeview = ttk.Treeview(self.under,columns=columns,show="headings")  # show is necessary

        for column in columns:
            self.treeview.heading(column, text = column)
        self.treeview.pack(expand = True, fill = "both")

        # insert 100 random values
        i = 0
        for key in self.period.results.keys():
            date = self.period.results[key]["date"]
            docID = self.period.results[key]["docID"]
            secCode = self.period.results[key]["secCode"]
            filerName = self.period.results[key]["filerName"]
            docDescription = self.period.results[key]["docDescription"]
            self.treeview.insert(parent="",
                        index = i,
                        values = (i, date,docID,secCode,filerName, docDescription))
            i += 1
        
        # ScrollBar
        # Create Scroll Bar
        y_scroll_bar = ctk.CTkScrollbar(self.under, orientation = "vertical", command = self.treeview.yview)    # Be aware of the yview
        self.treeview.configure(yscrollcommand = y_scroll_bar.set)    # Set the scroll bar's position to yview of self.treeview
        y_scroll_bar.place(relx = 1,rely = 0,relheight = 1,anchor = "ne")   # Place the Scroll Bar to the right side
        # Bind Scroll Bar to MouseWheel
        y_scroll_bar.bind("<MouseWheel>", lambda event: self.treeview.yview_scroll(-int(event.delta/60), "units"))

    def raise_suppress(self):
        if self.ar_num.get() == True:
            if_suppress = CTkMessagebox(title="Suppress Results View?", 
                                fg_color = "transparent",
                                message= "This program might be slow to run due to excessive columns in results.\nWould you like to directly save the results into csv files?",
                                icon="info", 
                                option_1="No", 
                                option_2="Yes")
            if if_suppress.get() == "Yes":
                self.suppress.select()
            else: pass

    def select_parse(self):
        self.select_win = ctk.CTkToplevel(self)
        self.select_win.title("Select")
        self.select_win.geometry("300x300")
        self.select_win.minsize(width=300,height=200)
        self.select_win.attributes('-topmost', True)

        select_frame = ctk.CTkFrame(self.select_win, fg_color = "transparent")
        ctk.CTkLabel(select_frame,text = "Annual Report(10k):").pack(expand = True, anchor = "w")
        self.ar_num = ctk.CTkCheckBox(select_frame, text="Numeric Data", 
                                      onvalue=True, offvalue=False, 
                                      checkbox_width = 18, checkbox_height=18,
                                      command = self.raise_suppress)
        self.ar_text = ctk.CTkCheckBox(select_frame, text="Textual Data", 
                                       onvalue=True, offvalue=False, 
                                       checkbox_width = 18, checkbox_height=18,
                                       command = self.check_textual)
        self.ar_num.pack(expand = True, anchor = "w", padx = 20)
        self.ar_text.pack(expand = True, anchor = "w", padx = 20)

        self.ar_mda = ctk.CTkCheckBox(select_frame, text="MD&A", onvalue=True, offvalue=False, checkbox_width = 18, checkbox_height=18)
        self.ar_risk = ctk.CTkCheckBox(select_frame, text="Risks", onvalue=True, offvalue=False, checkbox_width = 18, checkbox_height=18)
        self.ar_cg = ctk.CTkCheckBox(select_frame, text="CG", onvalue=True, offvalue=False, checkbox_width = 18, checkbox_height=18)

        self.ar_mda.pack(expand = True, anchor = "w", padx = 20)
        self.ar_risk.pack(expand = True, anchor = "w", padx = 20)
        self.ar_cg.pack(expand = True, anchor = "w", padx = 20)

        ctk.CTkLabel(select_frame,text = "Audit Report").pack(expand = True,anchor = "w")
        self.aud_all = ctk.CTkCheckBox(select_frame, text="All", onvalue=True, offvalue=False, checkbox_width = 18, checkbox_height=18)
        self.aud_all.pack(expand = True, anchor = "w", padx = 20)

        self.suppress = ctk.CTkCheckBox(select_frame, text="Suppress Output", onvalue=True, offvalue=False, checkbox_width = 18, checkbox_height=18)
        self.suppress.pack(expand = True, anchor = "w", padx = 20, pady = 10)

        select_frame.pack(expand = True, fill = "both", padx= 20, pady = 5)

        button_frame = ctk.CTkFrame(self.select_win, fg_color = "transparent")
        ctk.CTkButton(button_frame,text = "Continue", command = self.parse, fg_color = "#00a0a0").pack(side = "left", expand = True)
        ctk.CTkButton(button_frame,text = "Cancel", command = lambda: self.select_win.destroy(), fg_color = "#e2637c").pack(side = "left", expand = True)
        button_frame.pack(expand = True, fill = "both", padx= 10, pady = 5)
        
    # Build interaction between checkboxes
    def check_textual(self):
        if self.ar_text.get() == True:
            if_suppress = CTkMessagebox(title="Suppress Results View?", 
                                fg_color = "transparent",
                                message= "This program might be slow to run due to excessive columns in results.\nWould you like to directly save the results into csv files?",
                                icon="info", 
                                option_1="No", 
                                option_2="Yes")
            if if_suppress.get() == "Yes":
                self.suppress.select()
            else: pass
            self.ar_mda.select()
            self.ar_risk.select()
            self.ar_cg.select()
        else:
            self.ar_mda.deselect()
            self.ar_risk .deselect()
            self.ar_cg.deselect()

    def set_parse_win(self):
        self.parse_win = ctk.CTkToplevel(self)
        self.parse_win.title("Results")
        self.parse_win.geometry("1000x600")
        self.parse_win.minsize(width = 500, height = 500)
        self.parse_win.attributes('-topmost', True)

        # Add Export Option Menu
        menu = tk.Menu(self.parse_win)   # The main menu bar above
        export_menu = tk.Menu(menu,tearoff=False)  # tearoff is needed
        menu.add_cascade(label="Export", menu = export_menu )  # add the menu block to the menu
        export_menu.add_command(label = "Export as csv", command = self.save_csv)  

        self.parse_win.configure(menu=menu)

        self.parse_frame = ctk.CTkFrame(self.parse_win, fg_color="#e1edf0")   # Keep the same as self.upper
        self.parse_frame.pack(expand = True, fill = "both")
   
    # Need to add parsing button that do mda, risk and cd only
    def parse(self):
        self.select_win.destroy()
        kwargs = {button.cget("text"):button.get() for button in (self.ar_num, self.ar_text, self.aud_all, self.ar_mda, self.ar_risk, self.ar_cg)} 
        # keys = ("date","docID","secCode","filerName", "docDescription")
        result_dict = deepcopy(self.period.results)

        if kwargs.get("All") == True:
            audit_dict = self.period.get_auditors()
            for key in result_dict:
                result_dict[key].update(audit_dict[key]) if key in audit_dict else None

        elif kwargs.get("Numeric Data") == True:
            numeric_dict = self.period.get_numeric()
            for key in result_dict:
                result_dict[key].update(numeric_dict[key]) if key in numeric_dict else None

        elif kwargs.get("Textual Data") == True:
            textual_dict = self.period.get_textual()
            for key in result_dict:
                result_dict[key].update(textual_dict[key]) if key in textual_dict else None
        
        elif (kwargs.get("MD&A") == True) or (kwargs.get("Risks") == True) or (kwargs.get("CG")  == True):
            textual_dict = self.period.get_textual(items=kwargs)
            for key in result_dict:
                result_dict[key].update(textual_dict[key]) if key in textual_dict else None

        list_of_dict = [result_dict[key] for key in result_dict]
        self.df = pd.DataFrame(list_of_dict)

        if self.suppress.get() == True:
            self.save_csv()
        else:
            self.set_parse_win()
            self.set_parse_treeview()

    def truncate_string(self, s, max_length: int = 30):
        if isinstance(s,str):
            if len(s) > max_length:
                return s[:max_length] + f"\t total: {len(s)}" + '...'
            else: return s
        else: 
            return s

    # Add suppress argument because the low performance
    def set_parse_treeview(self): 
        display_df  = self.df.copy()
        display_df = display_df.map(self.truncate_string)

        parse_treeview = ttk.Treeview(self.parse_frame) 
        # Add columns
        parse_treeview["columns"] = list(display_df.columns)
        parse_treeview["show"] = "headings"

        for column in parse_treeview["columns"]:
            parse_treeview.heading(column, text=column)
            parse_treeview.column(column, width=100)
            
        # Add data to the Treeview
        for row in display_df.itertuples(index=False):
            parse_treeview.insert("", "end", values=row)

        parse_treeview.pack(expand = True, fill = "both")
        
        # Vertical Scroll Bar
        scroll_bar = ctk.CTkScrollbar(self.parse_win, orientation = "vertical", command = parse_treeview.yview)    # Be aware of the yview
        parse_treeview.configure(yscrollcommand = scroll_bar.set)                                                  # Set the scroll bar's position to yview of self.treeview
        scroll_bar.place(relx = 1,rely = 0,relheight = 1,anchor = "ne")                                                 # Place the Scroll Bar to the right side
        scroll_bar.bind("<MouseWheel>", lambda event: parse_treeview.yview_scroll(-int(event.delta/60), "units"))
        # Horizontal Scroll Bar
        x_scroll_bar = ctk.CTkScrollbar(self.parse_win, orientation = "horizontal", command = parse_treeview.xview)    # Be aware of the yview
        parse_treeview.configure(xscrollcommand = x_scroll_bar.set)    # Set the scroll bar's position to yview of self.treeview
        x_scroll_bar.place(relx = 0,rely = 1,relwidth = 1,anchor = "sw")   # Place the Scroll Bar to the right side

    def save_csv(self):
        files = [('csv UTF-16', '*.csv')] 
        try: 
            csv_dir = ctk.filedialog.asksaveasfilename(parent = self.parse_win,
                                                        defaultextension = files, 
                                                        filetypes = files)
        except:
            csv_dir = ctk.filedialog.asksaveasfilename(defaultextension = files, 
                                                        filetypes = files)     # In case self.parse_win does not exist
        if not os.path.exists(csv_dir):
            try:
                self.df.to_csv(csv_dir, 
                               encoding = "utf-16", 
                               index = False,sep = "\t")    # The seperation must be \t or it can not read in excel
            except Exception as e:
                CTkMessagebox(title="Save Error", 
                        fg_color = "transparent",
                        message= "Something Wrong",
                        icon="warning", 
                        option_1="Ok")
            else:
                CTkMessagebox(title="Saved", 
                        fg_color = "transparent",
                        message= "File is saved in csv format",
                        icon="check", 
                        option_1="Ok")
        else: pass
