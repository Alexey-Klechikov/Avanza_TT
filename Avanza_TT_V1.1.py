'''
Created by Alexey.Klechikov@gmail.com

Install with:
* Windows - pyinstaller --onefile --noconsole -i"C:\icon.ico" --add-data C:\icon.ico;images C:\Avanza_TT_V1.1.py
* MacOS - sudo pyinstaller --onefile --windowed Avanza_TT_V1.1.py

Requirements for a nice interface:
* PyQt<=5.12.2
'''

# import pkg_resources.py2_warn ## This is somehow required if I am "pyinstalling" in windows 10

from PyQt5 import QtCore, QtGui, QtWidgets, QtTest
import os, platform, sys, pkgutil, datetime, threading, h5py, requests, json
import pyqtgraph as pg
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from win10toast import ToastNotifier

QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

pd.set_option("display.max_rows", 2000, "display.max_columns", 2000)

''' Each ticker has some info, here we select only what we will use in this program '''
class Ticker:
    def __init__(self, tickerNumber, count, proxies):

        self.ticker = requests.get('https://www.avanza.se/_mobile/market/{0:s}/{1:d}'.format("stock", int(tickerNumber)), proxies=proxies).json()

        self.number = tickerNumber
        self.name = self.ticker['name']
        self.changePercent = self.ticker['changePercent']
        self.price_last = self.ticker['lastPrice']
        date = datetime.strptime(self.ticker['lastPriceUpdated'][:19], "%Y-%m-%dT%H:%M:%S")
        self.price_updateTime = date.strftime("%m/%d, %H:%M")
        self.count = count
        self.country = self.ticker['flagCode']
        self.currency = self.ticker['currency']

        # Some info is not presented in every ticker
        if 'keyRatios' in self.ticker:
            self.peRatio = np.NaN if 'priceEarningsRatio' not in self.ticker['keyRatios'] else self.ticker['keyRatios']['priceEarningsRatio']
            self.volatility = np.NaN if 'volatility' not in self.ticker['keyRatios'] else self.ticker['keyRatios']['volatility']
            self.directYield = np.NaN if 'directYield' not in self.ticker['keyRatios'] else self.ticker['keyRatios']['directYield']
        else: self.peRatio, self.volatility, self.directYield = np.NaN, np.NaN, np.NaN

        if 'company' in self.ticker: self.sector = np.NaN if 'sector' not in self.ticker['company'] else self.ticker['company']['sector']
        else: self.sector = np.NaN

        self.dividends = self.ticker["dividends"] if "dividends" in self.ticker else []
        self.reports = self.ticker["companyReports"] if "companyReports" in self.ticker else []
        self.price_oneWeek = self.ticker["priceOneWeekAgo"] if "priceOneWeekAgo" in self.ticker else np.NaN
        self.price_oneMonth = self.ticker["priceOneMonthAgo"] if "priceOneMonthAgo" in self.ticker else np.NaN
        self.price_sixMonth = self.ticker["priceSixMonthsAgo"] if "priceSixMonthsAgo" in self.ticker else np.NaN
        self.price_oneYear = self.ticker["priceOneYearAgo"] if "priceOneYearAgo" in self.ticker else np.NaN

        # Chartdata
        p, h = { "orderbookId": tickerNumber, "chartType": 'AREA', "chartResolution": 'DAY', "timePeriod": 'three_years'},  {"Content-Type": "application/json"}
        r = requests.post('https://www.avanza.se/ab/component/highstockchart/getchart/orderbook', data=json.dumps(p), headers=h, proxies=proxies).json()
        if 'dataPoints' in r:
            dataSeries = r['dataPoints']
            for x in dataSeries:
                x[0] = datetime.fromtimestamp(x[0] / 1000).isoformat()
            self.chartdata = pd.read_json(json.dumps(dataSeries))
            self.chartdata.columns = ['Date', 'Price']
            self.chartdata = self.chartdata.loc[pd.notnull(self.chartdata.Price)]

''' __For TimeAxis plotting__ '''
class TimeAxisItem(pg.AxisItem):
    def f_tickStrings(self, values, scale, spacing):
        return [datetime.fromtimestamp(value).date() for value in values]

''' Interface / Main Window '''
class Ui_MainWindow(QtWidgets.QMainWindow):

    currentDir = ""
    if platform.system() == 'Windows': currentDir, groupbox_osDisplacement = os.getcwd().replace("\\", "/") + "/", 0
    else:
        for i in sys.argv[0].split("/")[:-4]: currentDir += i + "/"
        groupbox_osDisplacement = 2

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
        MainWindow.resize(1092, 580)
        MainWindow.setMinimumSize(QtCore.QSize(1092, 580))
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
        self.Interface_TableMain = QtWidgets.QTableWidget(self.centralwidget)
        self.__create_element(self.Interface_TableMain, [5, 5, 815, 581], "Interface_TableMain", font=font_ee)
        self.Interface_TableMain.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.Interface_TableMain.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.Interface_TableMain.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.Interface_TableMain.verticalHeader().hide()

        # Block: Tickers management
        self.Interface_Label_TickersManagement = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_TickersManagement, [835, 3, 150, 22], "Interface_Label_TickersManagement", text="Tickers management:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_TickersManagement = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_TickersManagement, [830, 8, 255, 104], "Interface_GroupBox_TickersManagement", font=font_ee)

        ## Add / Remove ticker
        self.Interface_Label_Ticker = QtWidgets.QLabel(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Label_Ticker, [10, 23, 55, 22], "Interface_Label_Ticker", text="Ticker:", font=font_headline)
        self.Interface_Button_Ticker_Update = QtWidgets.QPushButton(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Button_Ticker_Update, [60, 23, 25, 22], "Interface_Button_Ticker_Update", text="+", font=font_headline)
        self.Interface_ComboBox_Ticker_ID = QtWidgets.QComboBox(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_ComboBox_Ticker_ID, [90, 23, 70, 22], "Interface_ComboBox_Ticker_ID", font=font_ee)

        self.Interface_LineEdit_Ticker_Amount = QtWidgets.QLineEdit(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_LineEdit_Ticker_Amount, [165, 23, 50, 22], "Interface_LineEdit_Ticker_Amount", font=font_ee, placeholder="Amount", alignment=QtCore.Qt.AlignCenter)
        self.Interface_Button_Ticker_Remove = QtWidgets.QPushButton(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Button_Ticker_Remove, [220, 23, 25, 22], "Interface_Button_Ticker_Remove", text="-", font=font_headline)

        self.Interface_Button_Ticker_Info = QtWidgets.QPushButton(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Button_Ticker_Info, [60, 50, 25, 22], "Interface_Button_Ticker_Info", text="?", font=font_headline)
        self.Interface_LineEdit_Ticker_Name = QtWidgets.QLineEdit(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_LineEdit_Ticker_Name, [90, 50, 155, 22], "Interface_LineEdit_Ticker_Name", font=font_ee, placeholder="Name / ID", alignment=QtCore.Qt.AlignCenter)

        ## Add / Remove currency ticker
        self.Interface_Label_Ticker_Currency = QtWidgets.QLabel(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Label_Ticker_Currency, [10, 77, 120, 22], "Interface_Label_Ticker_Currency", text="Currency Ticker:", font=font_headline)
        self.Interface_Button_Ticker_Currency_Add = QtWidgets.QPushButton(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Button_Ticker_Currency_Add, [125, 77, 25, 22], "Interface_Button_Ticker_Currency_Add", text="+", font=font_headline)
        self.Interface_LineEdit_Ticker_Currency_ID = QtWidgets.QLineEdit(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_LineEdit_Ticker_Currency_ID, [155, 77, 60, 22], "Interface_LineEdit_Ticker_Currency_ID", font=font_ee, placeholder="ID", alignment=QtCore.Qt.AlignCenter)
        self.Interface_Button_Ticker_Currency_Remove = QtWidgets.QPushButton(self.Interface_GroupBox_TickersManagement)
        self.__create_element(self.Interface_Button_Ticker_Currency_Remove, [220, 77, 25, 22], "Interface_Button_Ticker_Currency_Remove", text="-", font=font_headline)

        # Block: Update the table
        self.Interface_Label_UpdateTable = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_UpdateTable, [835, 120, 150, 22], "Interface_Label_UpdateTable", text="Update the table:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_UpdateTable = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_UpdateTable, [830, 125, 255, 78], "Interface_GroupBox_UpdateTable", font=font_ee)

        self.Interface_Button_Update_Now = QtWidgets.QPushButton(self.Interface_GroupBox_UpdateTable)
        self.__create_element(self.Interface_Button_Update_Now, [10, 23, 50, 22], "Interface_Button_Update_Now", text="Now", font=font_headline)
        self.Interface_Button_Update_Interval = QtWidgets.QPushButton(self.Interface_GroupBox_UpdateTable)
        self.__create_element(self.Interface_Button_Update_Interval, [110, 23, 80, 22], "Interface_Button_Update_Interval", text="Interval", font=font_headline)
        self.Interface_LineEdit_Update_Interval = QtWidgets.QLineEdit(self.Interface_GroupBox_UpdateTable)
        self.__create_element(self.Interface_LineEdit_Update_Interval, [195, 23, 50, 22], "Interface_LineEdit_Update_Interval", font=font_ee, placeholder="Minutes", alignment=QtCore.Qt.AlignCenter)

        self.Interface_CheckBox_ShowWarnings = QtWidgets.QCheckBox(self.Interface_GroupBox_UpdateTable)
        self.__create_element(self.Interface_CheckBox_ShowWarnings, [10, 50, 200, 22], "Interface_CheckBox_ShowWarnings", text="Warnings when drop by (%)", font=font_ee)
        self.Interface_LineEdit_ShowWarnings = QtWidgets.QLineEdit(self.Interface_GroupBox_UpdateTable)
        self.__create_element(self.Interface_LineEdit_ShowWarnings, [195, 50, 50, 22], "Interface_LineEdit_ShowWarnings", font=font_ee, text="-2", alignment=QtCore.Qt.AlignCenter)

        # Block: Balance
        self.Interface_Label_Balance = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Balance, [835, 208, 300, 22], "Interface_Label_Balance", text="Balance:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_UpdateTable = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_UpdateTable, [830, 215, 255, 202], "Interface_GroupBox_UpdateTable", font=font_ee)
        self.Interface_Button_UpdateHistory = QtWidgets.QPushButton(self.centralwidget)
        self.__create_element(self.Interface_Button_UpdateHistory, [995, 208, 90, 22], "Interface_Button_UpdateHistory", text="Upd. history", font=font_headline)
        self.Interface_GraphicsView_Balance = pg.PlotWidget(self.Interface_GroupBox_UpdateTable, axisItems={'bottom': TimeAxisItem(orientation='bottom')}, viewBox=pg.ViewBox())
        self.__create_element(self.Interface_GraphicsView_Balance, [2, 19, 252, 182], "Interface_GraphicsView_Balance")
        self.Interface_GraphicsView_Balance.getAxis("bottom").tickFont = font_graphs
        self.Interface_GraphicsView_Balance.getAxis("bottom").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Balance.getAxis("left").tickFont = font_graphs
        self.Interface_GraphicsView_Balance.getAxis("left").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Balance.showAxis("top")
        self.Interface_GraphicsView_Balance.getAxis("top").setTicks([])
        self.Interface_GraphicsView_Balance.showAxis("right")
        self.Interface_GraphicsView_Balance.getAxis("right").setTicks([])

        # Block: Dividents - Calendar
        self.Interface_Label_Dividends = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Dividends, [835, 422, 150, 22], "Interface_Label_Dividends", text="Dividends:", font=font_headline,
                              stylesheet="QLabel { color : blue; }")
        self.Interface_Button_Dividends = QtWidgets.QPushButton(self.centralwidget)
        self.__create_element(self.Interface_Button_Dividends, [935, 422, 150, 22], "Interface_Button_Dividends", text="Show calendar", font=font_headline)

        # Block: Reports - Calendar
        self.Interface_Label_Reports = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Reports, [835, 447, 150, 22], "Interface_Label_Reports", text="Reports:", font=font_headline,
                              stylesheet="QLabel { color : blue; }")
        self.Interface_Button_Reports = QtWidgets.QPushButton(self.centralwidget)
        self.__create_element(self.Interface_Button_Reports, [935, 447, 150, 22], "Interface_Button_Reports", text="Show calendar", font=font_headline)

        # Block: Proxy
        self.Interface_Label_Settings = QtWidgets.QLabel(self.centralwidget)
        self.__create_element(self.Interface_Label_Settings, [835, 472, 150, 22], "Interface_Label_Settings", text="Settings:", font=font_headline, stylesheet="QLabel { color : blue; }")
        self.Interface_GroupBox_Settings = QtWidgets.QGroupBox(self.centralwidget)
        self.__create_element(self.Interface_GroupBox_Settings, [830, 477, 255, 52], "Interface_GroupBox_Settings", font=font_ee)
        self.Interface_Label_Proxy = QtWidgets.QLabel(self.Interface_GroupBox_Settings)
        self.__create_element(self.Interface_Label_Proxy, [10, 23, 120, 22], "Interface_Label_Proxy", text="Proxy:", font=font_headline)
        self.Interface_LineEdit_Proxy = QtWidgets.QLineEdit(self.Interface_GroupBox_Settings)
        self.__create_element(self.Interface_LineEdit_Proxy, [60, 23, 190, 22], "Interface_LineEdit_Proxy", font=font_ee, placeholder="X.X.X.X:xxxx or proxy.com:xxxx", alignment=QtCore.Qt.AlignCenter)

        # Layout management (Stretching of the table with the window)
        self.table_verticalLayout = QtWidgets.QVBoxLayout()
        self.table_verticalLayout.setObjectName("Vertical_layout_1")
        self.table_verticalLayout.addWidget(self.Interface_TableMain)

        self.table_layoutMain = QtWidgets.QHBoxLayout(self.centralwidget)
        self.table_layoutMain.setObjectName("table_layoutMain")
        self.table_layoutMain.addLayout(self.table_verticalLayout)
        self.table_layoutMain.addSpacing(260)

        # MenuBar
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.__create_element(self.menubar, [0, 0, 699, 21], "menubar")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.__create_element(self.menuHelp, [999, 999, 999, 999], "menuHelp", title="Help")
        MainWindow.setMenuBar(self.menubar)
        self.actionVersion = QtWidgets.QAction(MainWindow)
        self.__create_element(self.actionVersion, [999, 999, 999, 999], "actionVersion", text="Version 1.1")
        self.menuHelp.addAction(self.actionVersion)
        self.menubar.addAction(self.menuHelp.menuAction())

        # StatusBar
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

''' Interface / Message Box (ticker details) '''
class Ui_MessageBox_Details(QtWidgets.QMessageBox):

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

        ticker_info = [("Name", ticker.name), ("Country", ticker.currency), ("Currency", ticker.country), ("Sector", ticker.sector), ("Key ratios", "Span"), ("P/E ratio", ticker.peRatio), ("Volatility", ticker.volatility), ("Direct yield", ticker.directYield), ("Price", "Span"), ("Last", ticker.price_last), ("One Week Ago", ticker.price_oneWeek), ("One Month Ago", ticker.price_oneMonth), ("Six Months Ago", ticker.price_sixMonth), ("One Year Ago", ticker.price_oneYear), ("Dividends (per share)", "Span")] + [(i['exDate'], i['amountPerShare']) for i in ticker.dividends]

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

        font_graphs = QtGui.QFont()
        font_graphs.setPixelSize(10)
        font_graphs.setBold(False)

        self.Interface_GroupBox_Chart = QtWidgets.QGroupBox(self)
        self.Interface_GroupBox_Chart.setGeometry(QtCore.QRect(300, -19, 500, 419))
        self.Interface_GroupBox_Chart.setObjectName('Interface_GroupBox_Chart')

        self.Interface_GraphicsView_Chart = pg.PlotWidget(self, axisItems={'bottom': TimeAxisItem(orientation='bottom')}, viewBox=pg.ViewBox())
        self.Interface_GraphicsView_Chart.setGeometry(QtCore.QRect(302, 2, 496, 396))
        self.Interface_GraphicsView_Chart.setObjectName('Interface_GraphicsView_Chart')
        self.Interface_GraphicsView_Chart.getAxis("bottom").tickFont = font_graphs
        self.Interface_GraphicsView_Chart.getAxis("bottom").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Chart.getAxis("left").tickFont = font_graphs
        self.Interface_GraphicsView_Chart.getAxis("left").setStyle(tickTextOffset=10)
        self.Interface_GraphicsView_Chart.showAxis("top")
        self.Interface_GraphicsView_Chart.getAxis("top").setTicks([])
        self.Interface_GraphicsView_Chart.showAxis("right")
        self.Interface_GraphicsView_Chart.getAxis("right").setTicks([])

        self.Interface_GraphicsView_Chart.getPlotItem().clear()
        points = pg.PlotCurveItem(x=[x.timestamp() for x in [datetime.strptime(i[:10], '%Y-%m-%d') for i in ticker.chartdata["Date"]]], y=list(ticker.chartdata["Price"]), pen=pg.mkPen(color=(0, 0, 255), width=2))

        self.Interface_GraphicsView_Chart.addItem(points)

    # Resize MessageBox window (Ugly solution, but the only I found)
    def event(self, _):
        result = QtGui.QMessageBox.event(self, _)

        size = [800, 450]
        self.setMinimumWidth(size[0])
        self.setMaximumWidth(size[0])
        self.setMinimumHeight(size[1])
        self.setMaximumHeight(size[1])
        self.resize(size[0], size[1])
        return result

''' Interface / Message Box (dividents calendar details) '''
class Ui_MessageBox_Dividents(QtWidgets.QMessageBox):

    # Table / Sorting
    sorting, sortTable, = {}, [0, QtCore.Qt.DescendingOrder]

    def __init__(self, tickers):

        QtGui.QMessageBox.__init__(self)

        self.setWindowTitle("Dividends Calendar")

        # when we create .exe with pyinstaller, we need to store icon inside it. Then we find it inside unpacked temp directory.
        for i in pkgutil.iter_importers():
            path = str(i).split("'")[1].replace("\\\\", "\\") if str(i).find('FileFinder') >= 0 else None
            if path != None: self.iconpath = path + "\\images\\icon.ico"
        self.setWindowIcon(QtGui.QIcon(self.iconpath))

        # Block: Table
        self.Interface_Table_MessageBox = QtGui.QTableWidget(self)
        self.Interface_Table_MessageBox.setGeometry(QtCore.QRect(0, 0, 500, 400))
        self.Interface_Table_MessageBox.setObjectName('Interface_Table_MessageBox')
        font_ee = QtGui.QFont()
        font_ee.setPointSize(9 if platform.system() == 'Windows' else 11)
        font_ee.setBold(False)
        self.Interface_Table_MessageBox.setFont(font_ee)
        self.Interface_Table_MessageBox.verticalHeader().hide()
        self.Interface_Table_MessageBox.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.Interface_Table_MessageBox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # retrieve all dividends dates and amounts
        dividends_data = []
        for index, ticker in enumerate(tickers):
            for i in ticker.dividends:
                dividends_data.append((i['exDate'], ticker.name, i['amountPerShare'], ticker.currency, ticker.count))

        col_param = [("Date", 70), ("Company", 160), ("Amount (per share)", 130), ("Currency", 60), ("My shares", 80)]

        self.Interface_Table_MessageBox.setColumnCount(len(col_param))
        self.Interface_Table_MessageBox.setRowCount(len(dividends_data))

        for i in range(len(dividends_data)):
            self.Interface_Table_MessageBox.setRowHeight(i, 1 if platform.system == "Windows" else 20)

            for j in range(len(col_param)):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setText(col_param[j][0])
                self.Interface_Table_MessageBox.setColumnWidth(j, col_param[j][1])
                self.Interface_Table_MessageBox.setHorizontalHeaderItem(j, item)

                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setData(QtCore.Qt.EditRole, str(dividends_data[i][j]))
                self.Interface_Table_MessageBox.setItem(i, j, item)

        self.Interface_Table_MessageBox.sortItems(self.sortTable[0], self.sortTable[1])
        self.Interface_Table_MessageBox.horizontalHeader().sectionClicked.connect(self.f_tableColumnSort)

    # Resize MessageBox window (Ugly solution, but the only I found)
    def event(self, _):
        result = QtGui.QMessageBox.event(self, _)

        size = [500, 450]
        self.setMinimumWidth(size[0])
        self.setMaximumWidth(size[0])
        self.setMinimumHeight(size[1])
        self.setMaximumHeight(size[1])
        self.resize(size[0], size[1])
        return result

    def f_tableColumnSort(self, logicalIndex):
        ''' Sort table on column header click '''
        if logicalIndex in self.sorting: self.sorting[logicalIndex] = QtCore.Qt.DescendingOrder if self.sorting[logicalIndex] == QtCore.Qt.AscendingOrder else QtCore.Qt.AscendingOrder
        else: self.sorting[logicalIndex] = QtCore.Qt.AscendingOrder

        self.sortTable = [logicalIndex, self.sorting[logicalIndex]]

        self.Interface_Table_MessageBox.sortItems(self.sortTable[0], self.sortTable[1])

''' Interface / Message Box (reports calendar details) '''
class Ui_MessageBox_Reports(QtWidgets.QMessageBox):

    # Table / Sorting
    sorting, sortTable, = {}, [0, QtCore.Qt.DescendingOrder]

    def __init__(self, tickers):

        QtGui.QMessageBox.__init__(self)

        self.setWindowTitle("Dividends Calendar")

        # when we create .exe with pyinstaller, we need to store icon inside it. Then we find it inside unpacked temp directory.
        for i in pkgutil.iter_importers():
            path = str(i).split("'")[1].replace("\\\\", "\\") if str(i).find('FileFinder') >= 0 else None
            if path != None: self.iconpath = path + "\\images\\icon.ico"
        self.setWindowIcon(QtGui.QIcon(self.iconpath))

        # Block: Table
        self.Interface_Table_MessageBox = QtGui.QTableWidget(self)
        self.Interface_Table_MessageBox.setGeometry(QtCore.QRect(0, 0, 500, 400))
        self.Interface_Table_MessageBox.setObjectName('Interface_Table_MessageBox')
        font_ee = QtGui.QFont()
        font_ee.setPointSize(9 if platform.system() == 'Windows' else 11)
        font_ee.setBold(False)
        self.Interface_Table_MessageBox.setFont(font_ee)
        self.Interface_Table_MessageBox.verticalHeader().hide()
        self.Interface_Table_MessageBox.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.Interface_Table_MessageBox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # retrieve all dividends dates and amounts
        reports_data = []
        for index, ticker in enumerate(tickers):
            for i in ticker.reports:
                reports_data.append((i['eventDate'], ticker.name, i['reportType']))

        col_param = [("Date", 70), ("Company", 160), ("Type", 130)]

        self.Interface_Table_MessageBox.setColumnCount(len(col_param))
        self.Interface_Table_MessageBox.setRowCount(len(reports_data))

        for i in range(len(reports_data)):
            self.Interface_Table_MessageBox.setRowHeight(i, 1 if platform.system == "Windows" else 20)

            for j in range(len(col_param)):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setText(col_param[j][0])
                self.Interface_Table_MessageBox.setColumnWidth(j, col_param[j][1])
                self.Interface_Table_MessageBox.setHorizontalHeaderItem(j, item)

                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setData(QtCore.Qt.EditRole, str(reports_data[i][j]).capitalize())
                self.Interface_Table_MessageBox.setItem(i, j, item)

        self.Interface_Table_MessageBox.sortItems(self.sortTable[0], self.sortTable[1])
        self.Interface_Table_MessageBox.horizontalHeader().sectionClicked.connect(self.f_tableColumnSort)

    # Resize MessageBox window (Ugly solution, but the only I found)
    def event(self, _):
        result = QtGui.QMessageBox.event(self, _)

        size = [360, 450]
        self.setMinimumWidth(size[0])
        self.setMaximumWidth(size[0])
        self.setMinimumHeight(size[1])
        self.setMaximumHeight(size[1])
        self.resize(size[0], size[1])
        return result

    def f_tableColumnSort(self, logicalIndex):
        ''' Sort table on column header click '''
        if logicalIndex in self.sorting: self.sorting[logicalIndex] = QtCore.Qt.DescendingOrder if self.sorting[logicalIndex] == QtCore.Qt.AscendingOrder else QtCore.Qt.AscendingOrder
        else: self.sorting[logicalIndex] = QtCore.Qt.AscendingOrder

        self.sortTable = [logicalIndex, self.sorting[logicalIndex]]

        self.Interface_Table_MessageBox.sortItems(self.sortTable[0], self.sortTable[1])

''' Main '''
class GUI(Ui_MainWindow):
    # Starting values
    TICKERS, CURRENCY_RATES_TICKERS, totalBalance, currentDir = {}, {}, "0 SEK", os.getcwd().replace("\\", "/") + "/"

    # Table / Sorting
    sorting, sortTable, = {}, [5, QtCore.Qt.AscendingOrder]

    def __init__(self):
        super(GUI, self).__init__()
        self.setupUi(self)

        # Triggers
        self.Interface_Button_Update_Now.clicked.connect(self.f_updateTableContent)
        self.Interface_Button_Update_Interval.clicked.connect(self.f_updateInterval)

        self.Interface_Button_Ticker_Update.clicked.connect(self.f_tickersAddRemove)
        self.Interface_Button_Ticker_Remove.clicked.connect(self.f_tickersAddRemove)
        self.Interface_Button_Ticker_Currency_Add.clicked.connect(self.f_tickersAddRemove)
        self.Interface_Button_Ticker_Currency_Remove.clicked.connect(self.f_tickersAddRemove)
        self.Interface_Button_Ticker_Info.clicked.connect(self.f_tickerDetailedInfo)
        self.Interface_Button_Dividends.clicked.connect(self.f_calendar)
        self.Interface_Button_Reports.clicked.connect(self.f_calendar)
        self.Interface_Button_UpdateHistory.clicked.connect(self.f_updateBalanceHistory)

        self.Interface_TableMain.horizontalHeader().sectionClicked.connect(self.f_tableColumnSort)

        self.Interface_LineEdit_Ticker_Name.textChanged.connect(self.f_tickersAddRemove)
        self.Interface_LineEdit_Proxy.editingFinished.connect(self.f_hdfFileUpdate)

        self.actionVersion.triggered.connect(self.f_menuInfo)

        # Initial calls
        self.f_hdfFileRead()
        self.f_fillTableTickers()

    def f_tickerDetailedInfo(self):

        if self.sender().objectName() == "Interface_Button_Ticker_Info":
            # If "sender" == Button "?"
            tickerData = Ticker(int(self.Interface_ComboBox_Ticker_ID.currentText()), 1, proxies=self.proxies)

        else:
            # If "sender" == Table: Find Ticker object by its name and show popup window with some more ticker info
            for index, i in enumerate(self.all_data):
                if i.number == int(self.sender().text()): tickerData = self.all_data[index]

        msgBox = Ui_MessageBox_Details(tickerData)
        msgBox.exec_()

    def f_tableColumnSort(self, logicalIndex):
        ''' Sort table on column header click '''
        if logicalIndex in self.sorting: self.sorting[logicalIndex] = QtCore.Qt.DescendingOrder if self.sorting[logicalIndex] == QtCore.Qt.AscendingOrder else  QtCore.Qt.AscendingOrder
        else: self.sorting[logicalIndex] = QtCore.Qt.AscendingOrder

        self.sortTable = [logicalIndex, self.sorting[logicalIndex]]

        self.Interface_TableMain.sortItems(self.sortTable[0], self.sortTable[1])

    def f_checkConnection(self):
        ''' Check if the internet connection can provide access to avanza.se '''

        # Proxies
        self.proxies = {"https": self.Interface_LineEdit_Proxy.text()}

        try:
            if requests.get('https://www.avanza.se/', proxies=self.proxies).status_code == 200: return True
        except:
            self.statusbar.showMessage("Check your internet connection or proxy settings")

        return False

    def f_calendar(self):
        msgBox = Ui_MessageBox_Dividents(self.all_data) if self.sender().objectName() == "Interface_Button_Dividends" else Ui_MessageBox_Reports(self.all_data)
        msgBox.exec_()

    def f_hdfFileRead(self):

        # Create Index dataset where all column names are stored
        indexes_arr = [n.encode("ascii", "ignore") for n in
                       ["ID", "Amount", "Name", "Change percent", "Price last", "Price one week", "Price one month", "Price six month", "Price one year",
                        "Price update time", "Country", "Currency", "P/E ratio", "Volatility", "Direct Yield", "Sector"]]

        # read HDF file if exists or create empty one
        if os.path.exists(self.currentDir + "user_data.hdf5"):

            with h5py.File("user_data.hdf5", "r") as file:
                # Take all info from last day
                for ticker, amount in file["tickers"][sorted(list(file["tickers"].keys()))[-3]]["Tickers Info"][:, :2]:
                    self.TICKERS[int(ticker)] = int(amount)

                # Take currencies from last day
                for ticker, _, name in file["tickers"][sorted(list(file["tickers"].keys()))[-3]]["Currency rates"][:, :]:
                    self.CURRENCY_RATES_TICKERS[int(ticker)] = str(name)

                # Proxies
                self.Interface_LineEdit_Proxy.setText("" if not file["proxy"][:, 0] else file["proxy"][:, 0][0])

        else:
            with h5py.File("user_data.hdf5", "w") as file:
                groupTickers = file.create_group("tickers")
                groupTickers.create_dataset("Tickers Indexes", data=indexes_arr)

                balanceArr_start = np.array([str(datetime.now().date()).encode("ascii", "ignore"), self.totalBalance.encode("ascii", "ignore")])
                groupTickers.create_dataset("Balance", (1, 2), maxshape=(None, 2), chunks=True, data=balanceArr_start)

                # Proxies
                file.create_dataset("proxy", (1, 1), dtype=h5py.special_dtype(vlen=str))

                # Fill the table with some default data
                self.TICKERS = {5361: 10, 293975: 10, 599956: 10, 549768: 10, 233288: 10}
                self.CURRENCY_RATES_TICKERS = {19000: "USD/SEK", 18998: "EUR/SEK", 53293: "NOK/SEK"}

    def f_hdfFileUpdate(self):

        # Tickers data
        dataArr = np.array([[i.number, i.count, i.name.encode("ascii", "ignore"), i.changePercent, i.price_last, i.price_oneWeek, i.price_oneMonth, i.price_sixMonth, i.price_oneYear, i.price_updateTime.encode("ascii", "ignore"), i.country.encode("ascii", "ignore"), i.currency.encode("ascii", "ignore"), i.peRatio, i.volatility, i.directYield, i.sector.encode("ascii", "ignore")] for i in self.all_data])

        # Currency data
        currencyArr = np.array([[self.currencyRates[i][1], self.currencyRates[i][0], i.encode("ascii", "ignore")] for i in self.currencyRates])

        with h5py.File("user_data.hdf5", "a") as file:

            # Work with datasets
            groupTickers = file["tickers"]

            # Update today's total balance (add new row or rewrite old one for today)
            if groupTickers["Balance"][groupTickers["Balance"].shape[0]-1, 0] != str(datetime.now().date()).encode("ascii", "ignore"):
                 groupTickers["Balance"].resize((groupTickers["Balance"].shape[0] + 1), axis = 0)

            groupTickers["Balance"][groupTickers["Balance"].shape[0] - 1, :] = [str(datetime.now().date()).encode("ascii", "ignore"), self.totalBalance.encode("ascii", "ignore")]

            # Send Balance points to print
            balanceArr_x, balanceArr_y = [], []
            for i in groupTickers["Balance"]:
                try:
                    balanceArr_y.append(int(str(i[1])[2:-5]))
                except: continue
                balanceArr_x.append(datetime.strptime(str(i[0])[2:-1] + " 12", '%Y-%m-%d %H'))

            if len(balanceArr_y) > 0: self.f_drawBalance(balanceArr_x, balanceArr_y)

            # Check if we already created the group with datasets today
            if "/tickers/" + str(datetime.now().date()) in file:
                subgroupLast = groupTickers[str(datetime.now().date())]

                subgroupLast["Tickers Info"].resize((len(dataArr)), axis = 0)
                subgroupLast["Tickers Info"][:] = dataArr

                subgroupLast["Currency rates"].resize((len(currencyArr)), axis = 0)
                subgroupLast["Currency rates"][:] = currencyArr
            else:
                subgroupLast = groupTickers.create_group(str(datetime.now().date()))

                subgroupLast.create_dataset("Tickers Info", data=dataArr, maxshape=(None, 16), chunks=True)
                subgroupLast.create_dataset("Currency rates", data=currencyArr, maxshape=(None, 3), chunks=True)

            # update Proxy
            file["proxy"][:, 0] = [self.Interface_LineEdit_Proxy.text().encode("ascii", "ignore")]

    def f_tickersAddRemove(self):

        self.statusbar.clearMessage()

        # Fill ticker Name / ID
        if self.sender().objectName() in ["Interface_LineEdit_Ticker_Name"]:
            # Search Ticker by Name, fill combobox, set ID
            if self.sender().objectName() == "Interface_LineEdit_Ticker_Name":

                self.Interface_ComboBox_Ticker_ID.clear()
                try:
                    _ = int(self.Interface_LineEdit_Ticker_Name.text())
                    self.Interface_ComboBox_Ticker_ID.addItem(self.Interface_LineEdit_Ticker_Name.text())
                except ValueError:
                    ticker = requests.get('https://www.avanza.se/_cqbe/search/global-search/global-search-template?query={}'.format(self.Interface_LineEdit_Ticker_Name.text()), proxies=self.proxies).json()

                    for SearchResultFilteredArr in [i["hits"] for i in ticker["resultGroups"] if i["instrumentType"] == 'STOCK']:

                        for SearchResult in SearchResultFilteredArr:
                            self.Interface_ComboBox_Ticker_ID.addItem(SearchResult['link']['orderbookId'])
            return

        # Data
        if self.sender().objectName() in ["Interface_Button_Ticker_Update", "Interface_Button_Ticker_Remove"]:
            try:
                if self.sender().objectName() == "Interface_Button_Ticker_Update": self.TICKERS[int(self.Interface_ComboBox_Ticker_ID.currentText())] = int(self.Interface_LineEdit_Ticker_Amount.text())
                else: del self.TICKERS[int(self.Interface_ComboBox_Ticker_ID.currentText())]
            except: self.statusbar.showMessage("Recheck Ticker format and Amount (both should be numbers)")

        # Currency
        elif self.sender().objectName() in ["Interface_Button_Ticker_Currency_Add", "Interface_Button_Ticker_Currency_Remove"]:
            try:
                if self.sender().objectName() == "Interface_Button_Ticker_Currency_Add":
                    self.CURRENCY_RATES_TICKERS[int(self.Interface_LineEdit_Ticker_Currency_ID.text())] = Ticker(int(self.Interface_LineEdit_Ticker_Currency_ID.text()), 1, proxies = {"https": self.Interface_LineEdit_Proxy.text()}).name
                else: del self.CURRENCY_RATES_TICKERS[int(self.Interface_LineEdit_Ticker_Currency_ID.text())]
            except: self.statusbar.showMessage("Recheck Currency Ticker format (should be a number)")

        self.f_fillTableTickers()

    def f_fillTableTickers(self):
        self.Interface_TableMain.clearContents()

        self.Interface_TableMain.setColumnCount(9)
        self.Interface_TableMain.setRowCount(len(self.TICKERS))

        offset = 20 if platform.system() == 'Windows' else 0
        self.MainWindow_size_height = max(421 + offset, 61 + offset + 20*len(self.TICKERS))
        self.resize(1092, 1000 if self.MainWindow_size_height > 1000 else self.MainWindow_size_height)

        column_names = ["ID", "Name", "Country", "Updated", "P/E", "Change today", "Price (SEK)", "Amount", "Total value (SEK)"]
        column_widths = [100, 200, 50, 80, 50, 90, 70, 60, 100]

        for i, tickerNumber in enumerate(self.TICKERS):

            self.Interface_TableMain.setRowHeight(i, 1 if platform.system == "Windows" else 20)

            for j in range(0, self.Interface_TableMain.columnCount()):
                item = QtWidgets.QTableWidgetItem()
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                item.setText(column_names[j])
                self.Interface_TableMain.setColumnWidth(j, column_widths[j])
                self.Interface_TableMain.setHorizontalHeaderItem(j, item)

                if j == 0:
                    item = QtWidgets.QPushButton(self.Interface_TableMain)
                    item.setText(str(tickerNumber))
                    self.Interface_TableMain.setCellWidget(i, j, item)
                else:
                    item = QtWidgets.QTableWidgetItem()
                    item.setTextAlignment(QtCore.Qt.AlignCenter)

                    if j == 7: content = self.TICKERS[tickerNumber]
                    else: content = ""

                    item.setFlags(QtCore.Qt.ItemIsEditable)
                    item.setData(QtCore.Qt.EditRole, content)
                    self.Interface_TableMain.setItem(i, j, item)

        self.f_updateTableContent()

    def f_updateTableContent(self):

        if not self.f_checkConnection(): return

        self.message, self.all_data, self.currencyRates, self.cell_buttons_collection, balance, self.totalBalance = "", [], {}, [], {"SEK": 0}, "0 SEK"

        def __update_thread__(ticker, TICKERS, all_data, currencyRates, proxies):

            if not all_data == False: # threads for DATA
                tickerData = Ticker(int(ticker), int(TICKERS[ticker]), proxies = proxies)
                all_data.append(tickerData)

            else: # threads for CURRENCY
                tickerData = Ticker(int(ticker), 1, proxies = proxies)
                currencyRates[tickerData.name] = [tickerData.price_last, tickerData.number]

        # Start data update CURRENCY in threads and Wait for all threads to quit
        for ticker in self.CURRENCY_RATES_TICKERS:
            x = threading.Thread(target=__update_thread__, args=(ticker, False, False, self.currencyRates, self.proxies))
            x.start()
        while threading.active_count() > 1: True

        # Start data update DATA in threads and Wait for all threads to quit
        for ticker in self.TICKERS.keys():
            x = threading.Thread(target=__update_thread__, args=(ticker, self.TICKERS, self.all_data, False, self.proxies))
            x.start()
        while threading.active_count() > 1: True

        # Fill the table
        for index, ticker in enumerate(self.all_data):
            item = QtWidgets.QPushButton(self.Interface_TableMain)
            item.setText(str(ticker.number))
            item.clicked.connect(self.f_tickerDetailedInfo)
            self.Interface_TableMain.setCellWidget(index, 0, item)
            self.Interface_TableMain.item(index, 1).setText(str(ticker.name))
            self.Interface_TableMain.item(index, 2).setText(str(ticker.country))
            self.Interface_TableMain.item(index, 3).setData(QtCore.Qt.EditRole, ticker.price_updateTime)
            self.Interface_TableMain.item(index, 4).setData(QtCore.Qt.EditRole, ticker.peRatio)
            self.Interface_TableMain.item(index, 5).setData(QtCore.Qt.EditRole, ticker.changePercent)

            if ticker.currency not in balance: balance[ticker.currency] = 0
            if ticker.currency + "/SEK" not in self.currencyRates and ticker.currency != "SEK":
                self.statusbar.showMessage("Missing Currency Ticker (" + ticker.currency + "/SEK)")
                price_last = str(ticker.price_last) + " " + str(ticker.currency)
                total = str(round(ticker.price_last * ticker.count, 2)) + " " + str(ticker.currency)
                balance[ticker.currency] += int(round(ticker.price_last * ticker.count))
            else:
                price_last = round(ticker.price_last * (1 if ticker.currency == "SEK" else self.currencyRates[ticker.currency + "/SEK"][0]), 2)
                total = round(ticker.price_last * ticker.count * (1 if ticker.currency == "SEK" else self.currencyRates[ticker.currency + "/SEK"][0]))
                balance["SEK"] += int(total)

            self.Interface_TableMain.item(index, 6).setData(QtCore.Qt.EditRole, price_last)
            self.Interface_TableMain.item(index, 7).setData(QtCore.Qt.EditRole, ticker.count)
            self.Interface_TableMain.item(index, 8).setData(QtCore.Qt.EditRole, total)

            # Color of the text ("Change today") is defined by its content. Black for other columns
            [self.Interface_TableMain.item(index, i).setForeground(QtGui.QColor(0, 0, 0)) for i in range(1, 9)]
            self.Interface_TableMain.item(index, 5).setForeground(
                QtGui.QBrush(QtGui.QColor(255, 0, 0) if ticker.changePercent < 0 else QtGui.QColor(0, 0, 255)))

            # Prepare message for toast notification
            try:
                _ = float(self.Interface_LineEdit_ShowWarnings.text())
            except:
                self.statusbar.showMessage("Warnings threshold should be a number")
                return

            if ticker.changePercent < float(self.Interface_LineEdit_ShowWarnings.text()):
                self.message += ticker.name + " " + str(ticker.changePercent) + "\n"

        # calculate "Balance"
        self.totalBalance = " + ".join([str(str(balance[i]) + " " + i) for i in balance if balance[i] != 0])

        self.Interface_Label_Balance.setText("Balance: " + str(self.totalBalance))

        # Sort the table for consistent view
        self.Interface_TableMain.sortItems(self.sortTable[0], self.sortTable[1])

        # Warning
        self.f_showWarnings("Significant drop today (by more than " + self.Interface_LineEdit_ShowWarnings.text() + "%)", self.message)

        # HDF write
        self.f_hdfFileUpdate()

        # Show "Update time" in status bar
        self.statusbar.showMessage(f"Last update at {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    def f_updateInterval(self):

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
            self.f_updateTableContent()
            QtTest.QTest.qWait(int(self.Interface_LineEdit_Update_Interval.text()) * 1000 * 60)

    def f_updateBalanceHistory(self):
        '''
        Used to fill balances for missing dates
        '''

        ### 1 - create full dates list

        USER_BALANCE = []
        with h5py.File("user_data.hdf5", "r") as file:
            # Take all info from last day
            for folder_date in [i for i in file["tickers"].keys() if not i in ["Balance", "Tickers Indexes"]]:
                for ticker, amount, currency in file["tickers"][folder_date]["Tickers Info"][:, [0, 1, 11]]:
                    USER_BALANCE.append([datetime.strptime(folder_date, '%Y-%m-%d'), int(ticker), int(amount), str(currency)[2:-1]])

        df_datesWithData = pd.DataFrame(USER_BALANCE, columns=("Date", "Ticker", "Amount", "Currency"))

        # Generate dataframe with only dusiness days starting from first run of the program
        df_datesEmpty = pd.bdate_range(start=df_datesWithData['Date'][0], end=datetime.now(), freq="B").to_frame(index=False, name="Date")
        # Merge dataframes to see when program wasnt working -> convert to dict
        df_datesFull = df_datesWithData.merge(df_datesEmpty, how="outer").sort_values("Date")

        # iterate by dates to fill missing dateInfo
        datesUnique, df_memo = list(df_datesFull["Date"].drop_duplicates()), ''
        if len(datesUnique) < 2: return
        for date in reversed(datesUnique):
            df_dateInfo = df_datesFull[df_datesFull["Date"] == date]
            if pd.isna(df_dateInfo.iloc[0].Ticker):
                df_memo["Date"].replace(df_memo.iloc[0].Date, date, inplace=True)
                df_datesFull = df_datesFull.merge(df_memo, how="outer")
            else:
                df_memo = df_dateInfo

        # Columns: "Date", "Ticker", "Amount", "Currency"
        df_datesFull = df_datesFull.sort_values("Date").dropna().reset_index(drop=True)

        ### 2 - find tickers price for the date

        # create DataFrame with trimmed chartdata (this data is already downloaded)
        df_pricesHistory, df_temp = pd.DataFrame(columns=["Date", "Ticker", "Price"]), ""
        for i in self.all_data:
            i.chartdata["Date"] = pd.to_datetime(i.chartdata["Date"])
            df_temp = i.chartdata[i.chartdata["Date"] >= df_datesWithData['Date'][0]]
            df_temp["Ticker"] = i.number
            # Columns: "Date", "Ticker", "Price"
            df_pricesHistory = pd.concat([df_pricesHistory, df_temp])

        # check fo missing chartdata (not in portfolio by today, so I keep only chartData)
        missingTickers = list(pd.concat([df_datesFull["Ticker"].drop_duplicates(), df_pricesHistory["Ticker"].drop_duplicates()]).drop_duplicates(keep=False))
        for ticker in missingTickers:
            tickerData = Ticker(int(ticker), 1, proxies=self.proxies)
            df_temp = tickerData.chartdata[tickerData.chartdata["Date"] >= df_datesWithData['Date'][0]]
            df_temp["Ticker"] = tickerData.number
            df_pricesHistory = pd.concat([df_pricesHistory, df_temp])

        ### 3 - merge 1 and 2, check for holidays (NaN for Price)

        # Columns: "Date", "Ticker", "Amount", "Price", "Currency"
        df_datesFullwPrices = pd.merge(df_datesFull, df_pricesHistory, how="left")
        df_datesFullwPrices = df_datesFullwPrices[df_datesFullwPrices["Date"] < datetime.today() - timedelta(days=1)]

        # Filter out only rows with NaN Prices. They are likely belongs to National Holidays in the Ticker'c country
        df_missingPrices = df_datesFullwPrices[pd.isnull(df_datesFullwPrices["Price"])]
        for date in list(df_missingPrices["Date"].drop_duplicates()):
            df_datesFullwPrices = df_datesFullwPrices[df_datesFullwPrices["Date"] != date]

        ### 4 - download currency rates for each date

        df_currencyRatesHistory, df_temp = pd.DataFrame(columns=["Date", "Currency", "Rate"]), ""
        for ticker in self.CURRENCY_RATES_TICKERS:
            tickerData = Ticker(int(ticker), 1, proxies=self.proxies)
            tickerData.chartdata["Date"] = pd.to_datetime(tickerData.chartdata["Date"])
            df_temp = tickerData.chartdata[tickerData.chartdata["Date"] >= df_datesWithData['Date'][0]].rename(columns={"Price": "Rate"})
            df_temp["Currency"] = tickerData.name.replace("/SEK", "")
            # Columns: "Date", "Currency", "Rate"
            df_currencyRatesHistory = pd.concat([df_currencyRatesHistory, df_temp])

        ### 5 - merge 3 and 4

        # Columns: "Date", "Ticker", "Amount", "Price", "Currency", "Rate"
        df_datesFullwPrices = pd.merge(df_datesFullwPrices, df_currencyRatesHistory, how="left")
        df_datesFullwPrices.loc[df_datesFullwPrices["Currency"] == "SEK", "Rate"] = 1

        ### 6 - sum by dates

        df_datesFullwPrices["Total"] = df_datesFullwPrices["Rate"] * df_datesFullwPrices["Price"] * df_datesFullwPrices["Amount"]
        # Columns: "Date", "Total"
        df_datesFullwPrices = df_datesFullwPrices.groupby(["Date"])["Total"].sum()

        ### 7 - write updated balances in hdf

        with h5py.File("user_data.hdf5", "a") as file:

            # Work with datasets
            groupTickersBalance = file["tickers"]["Balance"]
            groupTickersBalance.resize((0, 2))

            # Update today's total balance (add new row or rewrite old one for today)
            for row in df_datesFullwPrices.iteritems():
                groupTickersBalance.resize((groupTickersBalance.shape[0] + 1), axis=0)
                groupTickersBalance[groupTickersBalance.shape[0] - 1, :] = [str(row[0]).encode("ascii", "ignore"), str(str(round(row[1])) + " SEK").encode("ascii", "ignore")]

        ### 8 - call "Update Table" to get todays data
        self.f_updateTableContent()

    def f_drawBalance(self, balanceArr_x, balanceArr_y):

        self.Interface_GraphicsView_Balance.getPlotItem().clear()
        points = pg.PlotCurveItem(x=[x.timestamp() for x in balanceArr_x], y=balanceArr_y, pen=pg.mkPen(color=(0, 0, 255), width=2))
        self.Interface_GraphicsView_Balance.addItem(points)

    def f_menuInfo(self):

        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowIcon(QtGui.QIcon(self.iconpath))
        msgBox.setText("Tickers tracker for Avanza (Unofficial)\n\n"
                       "Alexey.Klechikov@gmail.com\n\n"
                       "Ticker number can be found in the address line of specific stock ('https://www.avanza.se/aktier/om-aktien.html/123456/Some_name' - here it is 123456)\n\n"
                       "You can support the project (swish 0702279150) if you found the app useful and/or want further development.\n\n"
                       "Check new version at https://github.com/Alexey-Klechikov/Avanza_TT/releases")
        msgBox.exec_()

    def f_showWarnings(self, category, message):

        if not self.Interface_CheckBox_ShowWarnings.isChecked(): return

        toaster = ToastNotifier()
        toaster.show_toast(category, message, duration=10, icon_path=self.iconpath, threaded=True)

if __name__ == "__main__":
    QtWidgets.QApplication.setStyle("Fusion")
    app = QtWidgets.QApplication(sys.argv)
    prog = GUI()
    prog.show()
    sys.exit(app.exec_())

