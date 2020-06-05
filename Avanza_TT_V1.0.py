'''
Created by Alexey.Klechikov@gmail.com

Install with:
* Windows - pyinstaller --onefile --noconsole -i"C:\icon.ico" --add-data C:\icon.ico;images C:\Avanza_TT_V1.0.py
* MacOS - sudo pyinstaller --onefile --windowed Avanza_TT_V1.0.py

Requirements for a nice interface:
* PyQt<=5.12.2
'''

from PyQt5 import QtCore, QtGui, QtWidgets, QtTest
import avanza, os, platform, sys, pkgutil, datetime, threading, h5py
import pyqtgraph as pg
import numpy as np
from datetime import datetime
from win10toast import ToastNotifier

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

''' Each ticker have some info, here we select only what we will use in this program '''
class Ticker:
    def __init__(self, ticker_number, count):
        self.ticker = avanza.Ticker(int(ticker_number))

        self.number = ticker_number
        self.name = self.ticker.name
        self.change_percent = self.ticker.change_percent
        self.price_last = self.ticker.last_price
        date = datetime.strptime(self.ticker.last_price_updated[:19], "%Y-%m-%dT%H:%M:%S")
        self.price_update_time = date.strftime("%m/%d, %H:%M")
        self.count = count
        self.country = self.ticker.flag_code
        self.currency = self.ticker.currency

        # Some info is not presented in every ticker
        if 'keyRatios' in self.ticker.info:
            self.PE_ratio = np.NaN if 'priceEarningsRatio' not in self.ticker.info['keyRatios'] else self.ticker.info['keyRatios']['priceEarningsRatio']
            self.volatility = np.NaN if 'volatility' not in self.ticker.info['keyRatios'] else self.ticker.info['keyRatios']['volatility']
            self.directYield = np.NaN if 'directYield' not in self.ticker.info['keyRatios'] else self.ticker.info['keyRatios']['directYield']
        else: self.PE_ratio, self.volatility, self.directYield = np.NaN, np.NaN, np.NaN

        if 'company' in self.ticker.info: self.sector = np.NaN if 'sector' not in self.ticker.info['company'] else self.ticker.info['company']['sector']
        else: self.sector = np.NaN

        self.dividends = self.ticker.info["dividends"] if "dividends" in self.ticker.info else []
        self.price_one_week = self.ticker.data["priceOneWeekAgo"] if "priceOneWeekAgo" in self.ticker.data else np.NaN
        self.price_one_month = self.ticker.data["priceOneMonthAgo"] if "priceOneMonthAgo" in self.ticker.data else np.NaN
        self.price_six_month = self.ticker.data["priceSixMonthsAgo"] if "priceSixMonthsAgo" in self.ticker.data else np.NaN
        self.price_one_year = self.ticker.data["priceOneYearAgo"] if "priceOneYearAgo" in self.ticker.data else np.NaN

''' __For plotting__ '''
class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).date() for value in values]

''' Interface / Main Window '''
class Ui_MainWindow(QtWidgets.QMainWindow):    

    current_dir = ""
    if platform.system() == 'Windows': current_dir, groupbox_os_displ = os.getcwd().replace("\\", "/") + "/", 0
    else:
        for i in sys.argv[0].split("/")[:-4]: current_dir += i + "/"
        groupbox_os_displ = 2

    def __create_element(self, object, geometry, object_name, text=None, font=None, placeholder=None, visible=None, stylesheet=None, checked=None, checkable=None, title=None, combo=None, enabled=None, alignment=None):

        object.setObjectName(object_name)

        if not geometry == [999, 999, 999, 999]:
            object.setGeometry(QtCore.QRect(geometry[0], geometry[1], geometry[2], geometry[3]))

        if not text == None: object.setText(text)
        if not title == None: object.setTitle(title)
        if not font == None: object.setFont(font)
        if not placeholder == None: object.setPlaceholderText(placeholder)
        if not visible == None: object.setVisible(visible)
        if not checked == None: object.setChecked(checked)
        if not checkable == None: object.setCheckable(checked)
        if not enabled == None: object.setEnabled(enabled)
        if not alignment == None: object.setAlignment(alignment)

        if not stylesheet == None: object.setStyleSheet(stylesheet)

        if not combo == None:
            for i in combo: object.addItem(str(i))

    def setupUi(self, MainWindow):

        # Fonts
        font_headline = QtGui.QFont()
        font_headline.setPointSize(10 if platform.system() == 'Windows' else 13)
        font_headline.setBold(True)

        font_graphs = QtGui.QFont()
        font_graphs.setPixelSize(10)
        font_graphs.setBold(False)

        font_ee = QtGui.QFont()
        font_ee.setPointSize(9 if platform.system() == 'Windows' else 11)
        font_ee.setBold(False)

        # Background and foreground for graphs
        pg.setConfigOption('background', (255, 255, 255))
        pg.setConfigOption('foreground', 'k')

        # Main Window
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1092, 441)
        MainWindow.setMinimumSize(QtCore.QSize(1092, 441))
        MainWindow.setMaximumSize(QtCore.QSize(1092, 1000))
        MainWindow.setWindowTitle("Tickers tracker for Avanza")

        # when we create .exe with pyinstaller, we need to store icon inside it. Then we find it inside unpacked temp directory.
        for i in pkgutil.iter_importers():
            path = str(i).split("'")[1].replace("\\\\", "\\") if str(i).find('FileFinder')>=0 else None
            if path != None: self.iconpath = path + "\\images\\icon.ico"
        MainWindow.setWindowIcon(QtGui.QIcon(self.iconpath))
        MainWindow.setIconSize(QtCore.QSize(30, 30))

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        # Block: Table
        self.Interface_Table_Main = QtWidgets.QTableWidget(self.centralwidget)
        self.__create_element(self.Interface_Table_Main, [5, 5, 815, 581], "Interface_Table_Main", font=font_ee)
        self.Interface_Table_Main.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.Interface_Table_Main.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.Interface_Table_Main.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.Interface_Table_Main.verticalHeader().hide()

        # Block: Tickers management
        self.Interface_Label_Tickers_management = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Tickers_management, [835, 3, 150, 22], "Interface_Label_Tickers_management", text="Tickers management:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_Tickers_management = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_Tickers_management, [830, 8, 255, 77], "Interface_GroupBox_Tickers_management", font=font_ee)

        ## Add / Remove ticker
        self.Interface_Label_Ticker = QtWidgets.QLabel(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Label_Ticker, [10, 23, 55, 22], "Interface_Label_Ticker", text="Ticker:", font=font_headline)
        self.Interface_Button_Ticker_Update = QtWidgets.QPushButton(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Button_Ticker_Update, [60, 23, 25, 22], "Interface_Button_Ticker_Update", text="+", font=font_headline)
        self.Interface_LineEdit_Ticker_ID = QtWidgets.QLineEdit(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_LineEdit_Ticker_ID, [90, 23, 60, 22], "Interface_LineEdit_Ticker_ID", font=font_ee, placeholder="ID", alignment=QtCore.Qt.AlignCenter)
        self.Interface_LineEdit_Ticker_Amount = QtWidgets.QLineEdit(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_LineEdit_Ticker_Amount, [155, 23, 60, 22], "Interface_LineEdit_Ticker_Amount", font=font_ee, placeholder="Amount", alignment=QtCore.Qt.AlignCenter)
        self.Interface_Button_Ticker_Remove = QtWidgets.QPushButton(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Button_Ticker_Remove, [220, 23, 25, 22], "Interface_Button_Ticker_Remove", text="-", font=font_headline)

        ## Add / Remove currency ticker
        self.Interface_Label_Ticker_Currency = QtWidgets.QLabel(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Label_Ticker_Currency, [10, 50, 120, 22], "Interface_Label_Ticker_Currency", text="Currency Ticker:", font=font_headline)
        self.Interface_Button_Ticker_Currency_Add = QtWidgets.QPushButton(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Button_Ticker_Currency_Add, [125, 50, 25, 22], "Interface_Button_Ticker_Currency_Add", text="+", font=font_headline)
        self.Interface_LineEdit_Ticker_Currency_ID = QtWidgets.QLineEdit(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_LineEdit_Ticker_Currency_ID, [155, 50, 60, 22], "Interface_LineEdit_Ticker_Currency_ID", font=font_ee, placeholder="ID", alignment=QtCore.Qt.AlignCenter)
        self.Interface_Button_Ticker_Currency_Remove = QtWidgets.QPushButton(self.Interface_GroupBox_Tickers_management)
        self.__create_element(self.Interface_Button_Ticker_Currency_Remove, [220, 50, 25, 22], "Interface_Button_Ticker_Currency_Remove", text="-", font=font_headline)

        # Block: Update the table
        self.Interface_Label_Update_table = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Update_table, [835, 93, 150, 22], "Interface_Label_Update_table", text="Update the table:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_Update_table = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_Update_table, [830, 98, 255, 78], "Interface_GroupBox_Update_table", font=font_ee)

        self.Interface_Button_Update_Now = QtWidgets.QPushButton(self.Interface_GroupBox_Update_table)
        self.__create_element(self.Interface_Button_Update_Now, [10, 23, 50, 22], "Interface_Button_Update_Now", text="Now", font=font_headline)
        self.Interface_Button_Update_Interval = QtWidgets.QPushButton(self.Interface_GroupBox_Update_table)
        self.__create_element(self.Interface_Button_Update_Interval, [110, 23, 80, 22], "Interface_Button_Update_Interval", text="Interval", font=font_headline)
        self.Interface_LineEdit_Update_Interval = QtWidgets.QLineEdit(self.Interface_GroupBox_Update_table)
        self.__create_element(self.Interface_LineEdit_Update_Interval, [195, 23, 50, 22], "Interface_LineEdit_Update_Interval", font=font_ee, placeholder="Minutes", alignment=QtCore.Qt.AlignCenter)

        self.Interface_CheckBox_Show_Warnings = QtWidgets.QCheckBox(self.Interface_GroupBox_Update_table)
        self.__create_element(self.Interface_CheckBox_Show_Warnings, [10, 50, 200, 22], "Interface_CheckBox_Show_Warnings", text="Warnings when drop by (%)", font=font_ee)
        self.Interface_LineEdit_Show_Warnings = QtWidgets.QLineEdit(self.Interface_GroupBox_Update_table)
        self.__create_element(self.Interface_LineEdit_Show_Warnings, [195, 50, 50, 22], "Interface_LineEdit_Show_Warnings", font=font_ee, text="-2", alignment=QtCore.Qt.AlignCenter)

        # Block: Balance
        self.Interface_Label_Balance = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Balance, [835, 183, 300, 22], "Interface_Label_Balance", text="Balance:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_Update_table = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_Update_table, [830, 188, 255, 202], "Interface_GroupBox_Update_table", font=font_ee)

        self.Interface_GraphicsView_Balance = pg.PlotWidget(self.Interface_GroupBox_Update_table, axisItems={'bottom': TimeAxisItem(orientation='bottom')}, viewBox=pg.ViewBox())
        self.__create_element(self.Interface_GraphicsView_Balance, [2, 19, 252, 182], "Interface_GraphicsView_Balance")
        self.Interface_GraphicsView_Balance.getAxis("bottom").tickFont = font_graphs
        self.Interface_GraphicsView_Balance.getAxis("bottom").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Balance.getAxis("left").tickFont = font_graphs
        self.Interface_GraphicsView_Balance.getAxis("left").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Balance.showAxis("top")
        self.Interface_GraphicsView_Balance.getAxis("top").setTicks([])
        self.Interface_GraphicsView_Balance.showAxis("right")
        self.Interface_GraphicsView_Balance.getAxis("right").setTicks([])

        # Layout management (Stretching of the table with the window)
        self.Vertical_layout_Table = QtWidgets.QVBoxLayout()
        self.Vertical_layout_Table.setObjectName("Vertical_layout_1")
        self.Vertical_layout_Table.addWidget(self.Interface_Table_Main)

        self.Layout_Main = QtWidgets.QHBoxLayout(self.centralwidget)
        self.Layout_Main.setObjectName("Layout_Main")
        self.Layout_Main.addLayout(self.Vertical_layout_Table)
        self.Layout_Main.addSpacing(260)

        # MenuBar
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.__create_element(self.menubar, [0, 0, 699, 21], "menubar")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.__create_element(self.menuHelp, [999, 999, 999, 999], "menuHelp", title="Help")
        MainWindow.setMenuBar(self.menubar)
        self.actionVersion = QtWidgets.QAction(MainWindow)
        self.__create_element(self.actionVersion, [999, 999, 999, 999], "actionVersion", text="Version 1.0")
        self.menuHelp.addAction(self.actionVersion)
        self.menubar.addAction(self.menuHelp.menuAction())

        # StatusBar
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

''' Interface / Message Box (ticker details) '''
class Ui_MessageBox(QtWidgets.QMessageBox):

    def __init__(self, ticker):

        QtGui.QMessageBox.__init__(self)

        self.setWindowTitle("Ticker {}".format(ticker.number))

        # when we create .exe with pyinstaller, we need to store icon inside it. Then we find it inside unpacked temp directory.
        for i in pkgutil.iter_importers():
            path = str(i).split("'")[1].replace("\\\\", "\\") if str(i).find('FileFinder') >= 0 else None
            if path != None: self.iconpath = path + "\\images\\icon.ico"
        self.setWindowIcon(QtGui.QIcon(self.iconpath))

        # Block: Table
        self.Interface_Table_MessageBox = QtGui.QTableWidget(self)
        self.Interface_Table_MessageBox.setGeometry(QtCore.QRect(0, 0, 300, 400))
        self.Interface_Table_MessageBox.setObjectName('Interface_Table_MessageBox')
        font_ee = QtGui.QFont()
        font_ee.setPointSize(9 if platform.system() == 'Windows' else 11)
        font_ee.setBold(False)
        self.Interface_Table_MessageBox.setFont(font_ee)
        self.Interface_Table_MessageBox.verticalHeader().hide()
        self.Interface_Table_MessageBox.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.Interface_Table_MessageBox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        ticker_info = [("Name", ticker.name), ("Country", ticker.currency), ("Currency", ticker.country), ("Sector", ticker.sector), ("Key ratios", "Span"), ("P/E ratio", ticker.PE_ratio), ("Volatility", ticker.volatility), ("Direct yield", ticker.directYield), ("Price", "Span"), ("Last", ticker.price_last), ("One Week Ago", ticker.price_one_week), ("One Month Ago", ticker.price_one_month), ("Six Months Ago", ticker.price_six_month), ("One Year Ago", ticker.price_one_year), ("Dividends (per share)", "Span")] + [(i['exDate'], i['amountPerShare']) for i in ticker.dividends]

        self.Interface_Table_MessageBox.setColumnCount(2)
        self.Interface_Table_MessageBox.setRowCount(len(ticker_info))

        col_param = [("Parameter", 100), ("Value", 200)]

        for i in range(0, len(ticker_info)):
            self.Interface_Table_MessageBox.setRowHeight(i, 1 if platform.system == "Windows" else 20)

            for j in [0, 1]:
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setText(col_param[j][0])
                self.Interface_Table_MessageBox.setColumnWidth(j, col_param[j][1])
                self.Interface_Table_MessageBox.setHorizontalHeaderItem(j, item)

                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setData(QtCore.Qt.EditRole, ticker_info[i][0 if j == 0 else 1])
                self.Interface_Table_MessageBox.setItem(i, j, item)

                if ticker_info[i][1] == "Span": self.Interface_Table_MessageBox.setSpan(i, 0, 1, 2)

    # Resize MessageBox window (Ugly solution, but the only I found)
    def event(self, _):
        result = QtGui.QMessageBox.event(self, _)

        self.setMinimumWidth(300)
        self.setMaximumWidth(300)
        self.setMinimumHeight(450)
        self.setMaximumHeight(450)
        self.resize(300, 450)
        return result

''' Main '''
class GUI(Ui_MainWindow):
    # Starting values
    TICKERS, CURRENCY_RATES_TICKERS, total_balance, current_dir = {}, {}, "0 SEK", os.getcwd().replace("\\", "/") + "/"

    # Table / Sorting
    sorting, sort_table = {}, [5, QtCore.Qt.AscendingOrder]

    def __init__(self):
        super(GUI, self).__init__()
        self.setupUi(self)

        # Triggers
        self.Interface_Button_Update_Now.clicked.connect(self.update_table_content)
        self.Interface_Button_Update_Interval.clicked.connect(self.update_interval)

        self.Interface_Button_Ticker_Update.clicked.connect(self.tickers_add_remove)
        self.Interface_Button_Ticker_Remove.clicked.connect(self.tickers_add_remove)
        self.Interface_Button_Ticker_Currency_Add.clicked.connect(self.tickers_add_remove)
        self.Interface_Button_Ticker_Currency_Remove.clicked.connect(self.tickers_add_remove)

        self.Interface_Table_Main.horizontalHeader().sectionClicked.connect(self.__table_column_sort__)

        self.actionVersion.triggered.connect(self.__menu_info__)

        # Initial calls
        self.hdf_file_read()
        self.fill_table_tickers()

    def __table_button_click__(self):
        # Find Ticker object by its name and show popup window with some more ticker info
        for index, i in enumerate(self.all_data):
            if i.number == int(self.sender().text()):
                msgBox = Ui_MessageBox(self.all_data[index])
                msgBox.exec_()

    def __table_column_sort__(self, logicalIndex):
        ''' Sort table on column header click '''
        if logicalIndex in self.sorting: self.sorting[logicalIndex] = QtCore.Qt.DescendingOrder if self.sorting[logicalIndex] == QtCore.Qt.AscendingOrder else  QtCore.Qt.AscendingOrder
        else: self.sorting[logicalIndex] = QtCore.Qt.AscendingOrder

        self.sort_table = [logicalIndex, self.sorting[logicalIndex]]

        self.Interface_Table_Main.sortItems(self.sort_table[0], self.sort_table[1])

    def hdf_file_read(self):

        # Create Index dataset where all column names are stored
        indexes_arr = [n.encode("ascii", "ignore") for n in
                       ["ID", "Amount", "Name", "Change percent", "Price last", "Price one week", "Price one month", "Price six month", "Price one year",
                        "Price update time", "Country", "Currency", "P/E ratio", "Volatility", "Direct Yield", "Sector"]]

        # read HDF file if exists or create empty one
        if os.path.exists(self.current_dir + "user_data.hdf5"):
            with h5py.File("user_data.hdf5", "r") as file:
                # Take all info from last day
                for ticker, amount in file["tickers"][sorted(list(file["tickers"].keys()))[-3]]["Tickers Info"][:, :2]:
                    self.TICKERS[int(ticker)] = int(amount)

                # Take currencies from last day
                for ticker, _, name in file["tickers"][sorted(list(file["tickers"].keys()))[-3]]["Currency rates"][:, :]:
                    self.CURRENCY_RATES_TICKERS[int(ticker)] = str(name)
        else:
            with h5py.File("user_data.hdf5", "w") as file:
                group_tickers = file.create_group("tickers")
                group_tickers.create_dataset("Tickers Indexes", data=indexes_arr)

                balance_arr_start = np.array([str(datetime.now().date()).encode("ascii", "ignore"), self.total_balance.encode("ascii", "ignore")])
                group_tickers.create_dataset("Balance", (1, 2), maxshape=(None, 2), chunks=True, data=balance_arr_start)

                # Fill the table with some default data
                self.TICKERS = {5361: 10, 293975: 10, 599956: 10, 549768: 10, 233288: 10}
                self.CURRENCY_RATES_TICKERS = {19000: "USD/SEK", 18998: "EUR/SEK", 53293: "NOK/SEK"}

    def hdf_file_update(self):

        # Tickers data
        data_arr = np.array([[i.number, i.count, i.name.encode("ascii", "ignore"), i.change_percent, i.price_last, i.price_one_week, i.price_one_month, i.price_six_month, i.price_one_year, i.price_update_time.encode("ascii", "ignore"), i.country.encode("ascii", "ignore"), i.currency.encode("ascii", "ignore"), i.PE_ratio, i.volatility, i.directYield, i.sector.encode("ascii", "ignore")] for i in self.all_data])

        # Currency data
        currency_arr = np.array([[self.currency_rates[i][1], self.currency_rates[i][0], i.encode("ascii", "ignore")] for i in self.currency_rates])

        with h5py.File("user_data.hdf5", "a") as file:

            # Work with datasets
            group_tickers = file["tickers"]

            # Update today's total balance (add new row or rewrite old one for today)
            if group_tickers["Balance"][group_tickers["Balance"].shape[0]-1, 0] != str(datetime.now().date()).encode("ascii", "ignore"):
                 group_tickers["Balance"].resize((group_tickers["Balance"].shape[0] + 1), axis = 0)

            group_tickers["Balance"][group_tickers["Balance"].shape[0] - 1, :] = [str(datetime.now().date()).encode("ascii", "ignore"), self.total_balance.encode("ascii", "ignore")]

            # Send Balance points to print
            balance_arr_x, balance_arr_y = [], []
            for i in group_tickers["Balance"]:
                try:
                    balance_arr_y.append(int(str(i[1])[2:-5]))
                except: continue
                balance_arr_x.append(datetime.strptime(str(i[0])[2:-1] + " 12", '%Y-%m-%d %H'))

            if len(balance_arr_y) > 0: self.__draw_balance__(balance_arr_x, balance_arr_y)

            # Check if we already created the group with datasets today
            if "/tickers/" + str(datetime.now().date()) in file:
                subgroup_last = group_tickers[str(datetime.now().date())]

                subgroup_last["Tickers Info"].resize((len(data_arr)), axis = 0)
                subgroup_last["Tickers Info"][:] = data_arr

                subgroup_last["Currency rates"].resize((len(currency_arr)), axis = 0)
                subgroup_last["Currency rates"][:] = currency_arr
            else:
                subgroup_last = group_tickers.create_group(str(datetime.now().date()))

                subgroup_last.create_dataset("Tickers Info", data=data_arr, maxshape=(None, 16), chunks=True)
                subgroup_last.create_dataset("Currency rates", data=currency_arr, maxshape=(None, 3), chunks=True)

    def tickers_add_remove(self):

        self.statusbar.clearMessage()

        # Data
        if self.sender().objectName() in ["Interface_Button_Ticker_Update", "Interface_Button_Ticker_Remove"]:
            try:
                if self.sender().objectName() == "Interface_Button_Ticker_Update": self.TICKERS[int(self.Interface_LineEdit_Ticker_ID.text())] = int(self.Interface_LineEdit_Ticker_Amount.text())
                else: del self.TICKERS[int(self.Interface_LineEdit_Ticker_ID.text())]
            except: self.statusbar.showMessage("Recheck Ticker format and Amount (both should be numbers)")

        # Currency
        elif self.sender().objectName() in ["Interface_Button_Ticker_Currency_Add", "Interface_Button_Ticker_Currency_Remove"]:
            try:
                if self.sender().objectName() == "Interface_Button_Ticker_Currency_Add":
                    self.CURRENCY_RATES_TICKERS[int(self.Interface_LineEdit_Ticker_Currency_ID.text())] = Ticker(int(self.Interface_LineEdit_Ticker_Currency_ID.text()), 1).name
                else: del self.CURRENCY_RATES_TICKERS[int(self.Interface_LineEdit_Ticker_Currency_ID.text())]
            except: self.statusbar.showMessage("Recheck Currency Ticker format (should be a number)")

        self.fill_table_tickers()

    def fill_table_tickers(self):
        self.Interface_Table_Main.clearContents()

        self.Interface_Table_Main.setColumnCount(9)
        self.Interface_Table_Main.setRowCount(len(self.TICKERS))

        offset = 20 if platform.system() == 'Windows' else 0
        self.MainWindow_size_height = max(421 + offset, 61 + offset + 20*len(self.TICKERS))
        self.resize(1092, 1000 if self.MainWindow_size_height > 1000 else self.MainWindow_size_height)

        column_names = ["ID", "Name", "Country", "Updated", "P/E", "Change today", "Price (SEK)", "Amount", "Total value (SEK)"]
        column_widths = [100, 200, 50, 80, 50, 90, 70, 60, 100]

        for i, ticker_number in enumerate(self.TICKERS):

            self.Interface_Table_Main.setRowHeight(i, 1 if platform.system == "Windows" else 20)

            for j in range(0, self.Interface_Table_Main.columnCount()):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setText(column_names[j])
                self.Interface_Table_Main.setColumnWidth(j, column_widths[j])
                self.Interface_Table_Main.setHorizontalHeaderItem(j, item)

                if j == 0:
                    item = QtWidgets.QPushButton(self.Interface_Table_Main)
                    item.setText(str(ticker_number))
                    self.Interface_Table_Main.setCellWidget(i, j, item)
                else:
                    item = QtWidgets.QTableWidgetItem()
                    item.setTextAlignment(QtCore.Qt.AlignCenter)

                    if j == 7: content = self.TICKERS[ticker_number]
                    else: content = ""

                    item.setFlags(QtCore.Qt.ItemIsEditable)
                    item.setData(QtCore.Qt.EditRole, content)
                    self.Interface_Table_Main.setItem(i, j, item)

        self.update_table_content()

    def update_table_content(self):

        self.message, self.all_data, self.currency_rates, self.cell_buttons_collection, balance, self.total_balance = "", [], {}, [], {"SEK": 0}, "0 SEK"

        def __update_thread__(ticker, TICKERS, all_data, currency_rates):

            if not all_data == False: # threads for DATA
                ticker_data = Ticker(int(ticker), int(TICKERS[ticker]))
                all_data.append(ticker_data)

            else: # threads for CURRENCY
                ticker_data = Ticker(int(ticker), 1)
                currency_rates[ticker_data.name] = [ticker_data.price_last, ticker_data.number]

        # Start data update CURRENCY in threads and Wait for all threads to quit
        for ticker in self.CURRENCY_RATES_TICKERS:
            x = threading.Thread(target=__update_thread__, args=(ticker, False, False, self.currency_rates))
            x.start()
        while threading.active_count() > 1: True

        # Start data update DATA in threads and Wait for all threads to quit
        for ticker in self.TICKERS.keys():
            x = threading.Thread(target=__update_thread__, args=(ticker, self.TICKERS, self.all_data, False))
            x.start()
        while threading.active_count() > 1: True

        # Fill the table
        for index, ticker in enumerate(self.all_data):
            item = QtWidgets.QPushButton(self.Interface_Table_Main)
            item.setText(str(ticker.number))
            item.clicked.connect(self.__table_button_click__)
            self.Interface_Table_Main.setCellWidget(index, 0, item)
            self.Interface_Table_Main.item(index, 1).setText(str(ticker.name))
            self.Interface_Table_Main.item(index, 2).setText(str(ticker.country))
            self.Interface_Table_Main.item(index, 3).setData(QtCore.Qt.EditRole, ticker.price_update_time)
            self.Interface_Table_Main.item(index, 4).setData(QtCore.Qt.EditRole, ticker.PE_ratio)
            self.Interface_Table_Main.item(index, 5).setData(QtCore.Qt.EditRole, ticker.change_percent)

            if ticker.currency not in balance: balance[ticker.currency] = 0
            if ticker.currency + "/SEK" not in self.currency_rates and ticker.currency != "SEK":
                self.statusbar.showMessage("Missing Currency Ticker (" + ticker.currency + "/SEK)")
                last_price = str(ticker.price_last) + " " + str(ticker.currency)
                total = str(round(ticker.price_last * ticker.count, 2)) + " " + str(ticker.currency)
                balance[ticker.currency] += int(round(ticker.price_last * ticker.count))
            else:
                last_price = round(ticker.price_last * (1 if ticker.currency == "SEK" else self.currency_rates[ticker.currency + "/SEK"][0]), 2)
                total = round(ticker.price_last * ticker.count * (1 if ticker.currency == "SEK" else self.currency_rates[ticker.currency + "/SEK"][0]))
                balance["SEK"] += int(total)

            self.Interface_Table_Main.item(index, 6).setData(QtCore.Qt.EditRole, last_price)
            self.Interface_Table_Main.item(index, 7).setData(QtCore.Qt.EditRole, ticker.count)
            self.Interface_Table_Main.item(index, 8).setData(QtCore.Qt.EditRole, total)

            # Color of the text ("Change today") is defined by its content. Black for other columns
            [self.Interface_Table_Main.item(index, i).setForeground(QtGui.QColor(0, 0, 0)) for i in range(1, 9)]
            self.Interface_Table_Main.item(index, 5).setForeground(
                QtGui.QBrush(QtGui.QColor(255, 0, 0) if ticker.change_percent < 0 else QtGui.QColor(0, 0, 255)))

            # Prepare message for toast notification
            try:
                _ = float(self.Interface_LineEdit_Show_Warnings.text())
            except:
                self.statusbar.showMessage("Warnings threshold should be a number")
                return

            if ticker.change_percent < float(self.Interface_LineEdit_Show_Warnings.text()):
                self.message += ticker.name + " " + str(ticker.change_percent) + "\n"

        # calculate "Balance"
        self.total_balance = " + ".join([str(str(balance[i]) + " " + i) for i in balance if balance[i] != 0])

        self.Interface_Label_Balance.setText("Balance: " + str(self.total_balance))

        # Sort the table for consistent view
        self.Interface_Table_Main.sortItems(self.sort_table[0], self.sort_table[1])

        # Warning
        self.show_warnings("Significant drop today (by more than " + self.Interface_LineEdit_Show_Warnings.text() + "%)", self.message)

        # HDF write
        self.hdf_file_update()

    def update_interval(self):

        if not self.Interface_LineEdit_Update_Interval.text(): self.Interface_LineEdit_Update_Interval.setText("60")

        try:
            _ = int(self.Interface_LineEdit_Update_Interval.text())
        except:
            self.statusbar.showMessage("Update interval should be a whole number")
            return

        if self.Interface_Button_Update_Interval.text() == "Interval":
            self.Interface_Button_Update_Interval.setText("Stop")
            self.Interface_Button_Update_Now.setDisabled(True)
        else:
            self.Interface_Button_Update_Interval.setText("Interval")
            self.Interface_Button_Update_Now.setDisabled(False)

        while self.Interface_Button_Update_Interval.text() == "Stop":
            self.update_table_content()
            QtTest.QTest.qWait(int(self.Interface_LineEdit_Update_Interval.text()) * 1000 * 60)

    def __draw_balance__(self, balance_arr_x, balance_arr_y):

        self.Interface_GraphicsView_Balance.getPlotItem().clear()

        spots = pg.ScatterPlotItem(x=[x.timestamp() for x in balance_arr_x], y=balance_arr_y, symbol="o", size=4, pen=pg.mkPen(0, 0, 255), brush=pg.mkBrush(0, 0, 255))
        self.Interface_GraphicsView_Balance.addItem(spots)

    def __menu_info__(self):

        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(self.iconpath))
        msgBox.setText("Tickers tracker for Avanza (Unofficial)\n\n"
                       "Alexey.Klechikov@gmail.com\n\n"
                       "Ticker number can be found in the address line of specific stock ('https://www.avanza.se/aktier/om-aktien.html/123456/Some_name' - here it is 123456)\n\n"
                       "You can support the project (swish 0702279150) if you found the app useful and/or want further development.\n\n"
                       "Check new version at https://github.com/Alexey-Klechikov/Avanza_TT/releases")
        msgBox.exec_()

    def show_warnings(self, category, message):

        if not self.Interface_CheckBox_Show_Warnings.isChecked(): return

        toaster = ToastNotifier()
        toaster.show_toast(category, message, duration=10, threaded=True)

if __name__ == "__main__":
    QtWidgets.QApplication.setStyle("Fusion")
    app = QtWidgets.QApplication(sys.argv)
    prog = GUI()
    prog.show()
    sys.exit(app.exec_())

