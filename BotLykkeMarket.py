from distutils.log import debug
import requests
import json
import time
import urllib.parse
import hashlib
import hmac
import base64
import os
from datetime import datetime
import urllib3

urllib3.disable_warnings()
http = urllib3.PoolManager()
#LYKKE API
APIKEY = "[insert LYKKE Key]"

class Protobot:
    api_sec = "[insert KRAKEN Secure Key]"
    api_key = "[insert KRAKEN Key]"
    api_url = "https://api.kraken.com"
    
    starttime = 0
    avg = 0.0
    rsiVal = 0.0
    rsiSekVal = 0.0
    price = 0.0
    lastPrice = 9999999
    buyPrice = 0.0
    sellPrice = 0.0
    rsiSell = 0.0
    rsiBuy = 0.0
    profit = 0.0
    stopLoss = 0.0
    loopTime = 0
    runTime = 0
    avgInterval = 0
    rsiInterval = 0
    currentCHFBalance = 0.0
    currentBTCBalance = 0.0
    btcOrderVol = 0.0
    orderAlreadyExists = False
    gainInPercent = 0
    sellVol = 0.0
    priceBefore = 0.0
    
    # Konstruktor
    def __init__(self, runTime, avgInterval, rsiInterval, rsiBuy, rsiSell, loopTime, stopLoss, profit):
        self.runTime = runTime
        self.avgInterval = avgInterval
        self.rsiInterval = rsiInterval
        self.rsiBuy = rsiBuy
        self.rsiSell = rsiSell
        self.loopTime = loopTime
        self.stopLoss = stopLoss
        self.profit = profit
        self.starttime = int(time.time())
        self.price = self.getPriceFromAPI()
        self.refreshBalance()

########################################################################################
            # LOG FUNCTIONS
########################################################################################

        # Loop Daten für jede Runde werden in externes File geschrieben
    def printConfigfile(self):
        f = open("Configfile.txt", "a")  
        f.write("Start Time:           ")
        f.write(str(datetime.fromtimestamp(time.time()))+ '\n') 
        f.write("Start Balance CHF     ")  
        f.write(str(self.currentCHFBalance)+ '\n') 
        f.write("Start BTC Balance     ")  
        f.write(str(self.currentBTCBalance)+ '\n')      
        f.write("BTC Order Vol         ")  
        f.write(str(self.btcOrderVol) + '\n')     
        f.write("Buy at RSI:           ")
        f.write(str(self.rsiBuy)+ '\n')
        f.write("Sell at RSI:          ")
        f.write(str(self.rsiSell)+ '\n')
        f.write("Take Profit at:       ")
        f.write(str(self.profit)+ '\n')
        f.write("Stop Loss:            ")
        f.write(str(self.stopLoss)+ '\n')
        f.write("Loop Time:            ")
        f.write(str(self.loopTime)+ '\n')      
        f.write("AVG Days:             ")
        f.write(str(self.rsiInterval)+ '\n')  
        f.write("RSI Days:             ")
        f.write(str(self.avgInterval)+ '\n')         
        f.write('\n')
        f.close()
        
    # Loop Daten für jede Runde werden in externes File geschrieben
    def printLoopInfo(self):
        f = open("Loop_Logs.txt", "a")     
        f.write("Loop Time:"+str(datetime.fromtimestamp(time.time())))
        f.write("||AVG:"+str(self.getAvg()))
        f.write("||Current Price:"+str(self.getPrice()))
        f.write("||Last Price:"+str(self.getLastPrice()))
        f.write("||RSI Long:"+str(self.getRSI()))
        f.write("||CHF Balance: "+str(self.currentCHFBalance))
        f.write("||BTC Balance: "+str(self.currentBTCBalance))
        f.write("||BTC Order Vol:"+str(self.btcOrderVol))
        f.write("||Buy at RSI:"+str(self.rsiBuy))
        f.write("||Sell at RSI:"+str(self.rsiSell))
        f.write("||Order Already Exists:"+str(self.orderAlreadyExists))
        f.write('\n')
        f.close()

        # Loop Daten für jede Runde werden in externes File geschrieben
    def printHistoryData(self):
        f = open("history_data.txt", "a")     
        f.write(str(datetime.fromtimestamp(time.time())))
        f.write(","+str(self.getAvg()))
        f.write(","+str(self.getPrice()))
        f.write(","+str(self.getLastPrice()))
        f.write('\n')
        f.close()

    # Buy Daten in File schreiben
    def printBuyOrderData(self, profit):
        #Daten ins File schreiben
        f = open("Trade_Logs.txt", "a")
        f.write("||Balance:"+str(self.currentCHFBalance))
        f.write("||BUY  Time:"+str(datetime.fromtimestamp(time.time())))
        f.write("||BUY  Price:"+str(self.getBuyPrice()))
        f.write("||Take :"+str(round(self.getBuyPrice() * profit, 1)))
        f.write("||OrderState:"+str(self.orderAlreadyExists))
        f.write('\n')
        f.close()

    # Sell Daten in file schreiben
    # Param sellType 1 = Sell durch MAVG, 2 = Sell durch StopLoss
    def printSellOrderData(self, sellType):
        f = open("Trade_Logs.txt", "a")
        f.write("||Balance:"+str(self.currentCHFBalance))
        f.write("||SELL Time:"+str(datetime.fromtimestamp(time.time())))
        f.write("||SELL Price:"+str(self.getSellPrice()))
        f.write("||Selltype:"+str(sellType))
        f.write("||OrderState:"+str(self.orderAlreadyExists))
        f.write("||Gain:"+str(round(self.gainInPercent, 3))+"%")
        f.write('\n')
        f.close()

    # Error Daten in File schreiben
    def printError(self, exceptionType):
        #Daten ins File schreiben
        f = open("Public_API_Error_Logs.txt", "a")
        f.write(str(datetime.fromtimestamp(time.time())))
        f.write("||Error:")
        f.write("||"+str(exceptionType))
        f.write('\n')
        f.close()

    def log(self, orderType, orderStateText, orderVol):
        f = open("Private_API_Logs.txt", "a")
        f.write(str(datetime.fromtimestamp(time.time())))
        f.write("||"+orderType)
        f.write("||"+orderStateText)
        f.write("|| OrderVol "+orderVol)
        f.write('\n')
        f.close()

########################################################################################
            # ALL API REQUESTS
########################################################################################

    # OrderFunction
    def get_kraken_signature(self, urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    # OrderFunction
    def kraken_request(self, uri_path, data, api_key, api_sec):
        headers = {}
        headers['API-Key'] = api_key
        # Hier wird Signatur angefordert
        headers['API-Sign'] = self.get_kraken_signature(uri_path, data, api_sec)             
        req = requests.post((self.api_url + uri_path), headers=headers, data=data)
        return req

    # Holt aktuellen Preis von KRAKEN API und Rundet auf 0 Kommastellen
    def getPriceFromAPI(self):
        resp = requests.get('https://api.kraken.com/0/public/Ticker?pair=BTCCHF') # API Request KRAKEN
        return round(float(json.dumps(resp.json()["result"]["XBTCHF"]["a"][0])[1:-1]),0) # Verarbeitung JSON Object von Kraken Request

    def getBalance(self): #untested coz no api key given
        try:
            resp = requests.get('https://hft-apiv2.lykke.com/api/balance', headers = {'Authorization' : "Bearer " + APIKEY})
            balance = float(json.dumps(resp.json()["payload"][1]["available"]))
        except:
            self.printError("LYKKE API Error in -> get Balance()")
            self.printError(json.dumps(resp.json()))
            self.printError()

            time.sleep(5)
        return balance
   
########################################################################################
            # STRATEGIE MOVING AVG
########################################################################################

    # Berechnet AVG Value
    #@ Param val = Grösse Intervall Moving AVG
    #@ Return balance in CHF
    def getAvgFromAPI(self,val):
        hoursInUnix = (86400/24) * val # 86400 = 1 Tag
        since = time.time() - hoursInUnix
        url ='https://api.kraken.com/0/public/OHLC?pair=BTCCHF&interval=60&since='
        resp = requests.get(url + str(since)) # API Request KRAKEN
        sum = 0.0
        # @ MAVG For Loop Param -> 15 h = 15h/1h(intervall=60min) = 15 Schritte
        for i in range(val): # Summiert Schlusspreis von allen h auf
            sum += float(json.dumps(resp.json()["result"]["XBTCHF"][i][4])[1:-1]) # Verarbeitung JSON Object von Kraken Request
        return sum/val # Durchschnitt berechnen

########################################################################################
            # STRATEGIE RSI
########################################################################################

    # @Param Anzahl Tage RSI
    def calcRSI(self, val):
        sumUp = 0.0
        sumDown = 0.0
        # Unixtime in h berechnen 86400/24
        hoursInUnix = (86400/24) * val # 86400 = 1 Tag
        hoursAmount = val

        # Holt Jsonfile Parameter in URL beachten, Intervall 24h -> intervall=1440, OHLC Daten aus X Tagen -> since= @Param days
        # @ RSI Request Param -> 3 Tage = 72h/4h(intervall=240min) = 18 Schritte
        # @ RSI Info Rsi muss zwischen 10 und 25 Schritte/Tage/Stunden/oderirgenwas haben um effizient zu sein
        since = time.time() - hoursInUnix
        resp = requests.get('https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60&since='+str(since)) 
        data = resp.json()
        # @ RSI For Loop Param -> 3 Tage = 72h/4h(intervall=240min) = 18 Schritte, -1 wegen Json Object 0-17 für 18 schritte
        # @ RSI For Loop Param -> 1 Tag = 24h/4h(intervall=240min) = 6 Schritte, -1 wegen Json Object 0-5 für 6 schritte
        # @ RSI For Loop Param -> 15 h = 15 Schritte, -1 wegen Json Object 0-14 für 15 schritte
        # Weil wir bei max mit i+1 beginnen
        for i in range(15-1):
            max = float(json.dumps(data["result"]["XXBTZUSD"][i+1][4])[1:-1])
            min = float(json.dumps(data["result"]["XXBTZUSD"][i][4])[1:-1])
            if (max > min):
                sumUp += max - min
                sumDown += 0
            elif (max < min):
                sumDown += min - max
                sumUp += 0
        avgUp = sumUp / hoursAmount
        avgDown = sumDown / hoursAmount
        rsi = avgUp / (avgUp + avgDown)
        return rsi

########################################################################################
            # GET FUNCTIONS
########################################################################################

    def getBuyPrice(self):
        return self.buyPrice

    def getSellPrice(self):
        return self.sellPrice

    def getPrice(self):
        return self.price

    def getAvg(self):
        return self.avg

    def getLastPrice(self):
        return self.lastPrice

    def getRSI(self):
        return self.rsiVal

    def getProfit(self):
        return self.profit

    def getRunTime(self):
        return self.runTime

########################################################################################
            # TRIGGER FUNCTION
########################################################################################

    def checkTrigger(self):
        # BUY Überprüft ob PRICE den AVG von UNTEN nach OBEN schneidet falls true dann BUY
        # orderAlreadyExists = Überprüft ob bereits eine Order ausgeführt wurde oder nicht
        if (self.price >= self.getAvg() 
        and self.getLastPrice() <= self.getAvg() 
        and self.orderAlreadyExists == False 
        and self.getRSI() < self.rsiBuy):
            self.buyPrice = self.price
            self.buy()
            self.refreshBalance()
        
        # SELL durch x% Gewinn & RSI & MAVG
        elif (self.getBuyPrice() * self.getProfit() <= self.price and self.orderAlreadyExists == True and self.getRSI() > self.rsiSell):
            self.sellPrice = self.price
            self.sell("GainTrade")
            self.refreshBalance()
        
        # SELL durch StopLoss
        # orderAlreadyExists = Überprüft ob bereits eine Order ausgeführt wurde oder nicht

        elif (self.price <= (self.getBuyPrice() * self.stopLoss) and self.orderAlreadyExists == True):
            self.sellPrice = self.price
            self.sell("StopLoss")
            self.refreshBalance()

        # Testet ob Stoploss korrekt ausgeführt wird
        self.checkStopLoss()

    def checkStopLoss(self):
        print(self.getBuyPrice())
        print("<=")
        print(self.getBuyPrice() * self.stopLoss)
                                   
########################################################################################
            # BUY and SELL Order FUNCTION
########################################################################################

    # BuyOrderFunction
    # "https://hft-apiv2.lykke.com/api"
    def buy(self):
        self.currentCHFBalance = round(self.getBalance(), 4)
        self.btcOrderVol = round((self.currentCHFBalance * 0.95) / self.price, 5)
        self.sellVol = self.btcOrderVol
        self.priceBefore = self.currentCHFBalance
        resp = requests.post('https://hft-apiv2.lykke.com/api/orders/market', headers = {'Authorization' : "Bearer " + APIKEY}, json = {            
            "assetPairId": "BTCCHF",
            "side": "Buy",
            "volume": str(self.sellVol)
            })
        self.orderAlreadyExists = True
        self.log("BUY ",str(resp.json()), str(self.btcOrderVol))
        self.printBuyOrderData(self.stopLoss, self.profit)
        time.sleep(240)
        
    # SellOrderFunction
    def sell(self, orderType):
        # API Request SELL
        resp = requests.post('https://hft-apiv2.lykke.com/api/orders/market', headers = {'Authorization' : "Bearer " + APIKEY}, json = {            
            "assetPairId": "BTCCHF",
            "side": "Sell",
            "volume": str(self.sellVol)
            })
        groundNumber = self.currentCHFBalance # Lokale Var für Gewinn berechnen Value = alter Kontostand
        # Kontostand aktualisieren
        self.currentCHFBalance = round(self.getBalance(), 4)
        # Gewinn berechnen in %
        self.gainInPercent = round((((100/self.priceBefore) * self.currentCHFBalance) - 100), 3)
        self.orderAlreadyExists = False
        self.log("SELL " + str(orderType), str(resp.json()), str(self.btcOrderVol))
        self.printSellOrderData("MAVG")
        time.sleep(240)

########################################################################################
            # Refresh Functions
########################################################################################

    # Guthaben aktualisieren für nächsten Einsatz
    def refreshBalance(self):
        self.currentCHFBalance = self.getBalance()
        self.currentBTCBalance =round((self.currentCHFBalance) / self.price, 5)
        self.btcOrderVol = round((self.currentCHFBalance * 0.8) / self.price, 5)

########################################################################################
            # MAIN LOOP
########################################################################################

    def go(self):
        print("<-- Programm startet   -->")
        print("<-- Programm läuft.... -->")
        self.printConfigfile()
        while time.time() < (self.starttime + self.getRunTime()):
            try:
                self.avg = round(self.getAvgFromAPI(self.avgInterval),2)
            except:
                self.printError("AVG in go()")
                time.sleep(5)
            try:
                self.rsiVal = round(self.calcRSI(self.rsiInterval),2)
            except:
                self.printError("RSI in go()")
                time.sleep(5)
            time.sleep(self.loopTime)
            try:
                self.price = self.getPriceFromAPI()
            except:
                self.printError("PriceFromAPI in go() after Sleep")
            self.currentBTCBalance = round((self.currentCHFBalance)/self.price, 5)
            self.printLoopInfo()
            self.printHistoryData()
            self.checkTrigger()
            self.lastPrice = self.price
        print("<-- Program terminiert -->")

########################################################################################
            # MAIN FUNCTION
########################################################################################

if __name__ == "__main__":
    # @Param "laufzeit" in Sekunden
    # @Param "Mavg" in Tagen
    # @Param "RSI"  in h 
    # @Param "RSI Buy"  Zahl zwischen 1-100 Wenn (RSI < x) dann Buy
    # @Param "RSI Sell"  Zahl zwischen 1-100 Wenn (RSI > x) dann Sell
    # @Param "LoopTime" in Sekunden
    # @Param "Stop Loss" in Prozent -> Bsp 0.95 für -5%
    # @Param "Profit" in Prozent -> Bsp 1.03 für +3%

    # @Param       Laufzeit,  Mavg,  RSI Long,     RSI Buy(x), RSI Sell(x), Looptime, StopLoss, Profit
    bot = Protobot(1296000,   15,        15,          0.8,         0.2,        60,      0.95,    1.005)
    bot.go()
    
