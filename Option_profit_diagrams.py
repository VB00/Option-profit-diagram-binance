import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from collections.abc import Iterable
import requests
import pandas as pd
import time
import re
import random

def round_it(a):
    return round(a,2)

def calculate_sigma(name):
    
    pair = yf.download(name+'-USD')
    S0 = pair['Close'][-1]
    vol = pair[-7:]['High'] - pair[-7:]['Low'] 
    global_vol = pair['High'] - pair['Low'] 

    mean_global = 100*global_vol.mean() / pair['Close'].mean()
    mean_week = 100*vol.mean() / pair[-7:]['Close'].mean()

    expected_sigma_per_day = (-0.3 + (mean_global+mean_week)/2) / 100
    return expected_sigma_per_day, S0

class Profit (object):
    def __init__(self,K,T, cost_per_contract,num_of_contracts,is_call, crypto, option_name):
        self.K = K
        self.T = T
        self.cost_per_contract = cost_per_contract
        self.num_of_contracts = num_of_contracts
        self.is_call = is_call
        self.crypto = crypto
        self.option_name = option_name
    #fee structure
    def transaction_fee(self):
        Transaction_Fee_Rate = 0.0002
        Index_Price = self.S0
        Option_Traded_Price = self.cost_per_contract
        Option_Traded_Size = self.num_of_contracts

        Transaction_Fee = min(Transaction_Fee_Rate * Index_Price, 0.1 * Option_Traded_Price) * Option_Traded_Size

        return Transaction_Fee

    def exercise_fee(self, final_payoff, S1):
        Exercise_Fee_Rate = 0.00015
        Settlement_Price = S1
        Option_Value = final_payoff
        Position_Size = self.num_of_contracts
        Exercise_Fee = min(Exercise_Fee_Rate * Settlement_Price, 0.1 * Option_Value) * Position_Size
        return Exercise_Fee



    def profit(self,**kwargs):
        self.levels = kwargs.get('levels')
        Call_Put =  1 if self.is_call else -1 
        sigma, self.S0 = calculate_sigma(self.crypto)
        range_1 = self.K -  sigma * self.S0 * self.T
        range_2 = self.K + sigma  * self.S0 * self.T
        try:
            x = np.arange(min(range_1,range_2, min(self.levels)),max(range_1,range_2, max(self.levels)))
        except:
            x = np.arange(min(range_1,range_2),max(range_1,range_2))

        def calculate_y(x):
            save_profit = []
            x = x if isinstance(x,Iterable) else [x]
            for S1 in x:
                final_payoff = max(Call_Put * (S1 - self.K),0)
                profit = (final_payoff - self.cost_per_contract) * self.num_of_contracts - self.transaction_fee() - self.exercise_fee(final_payoff,S1)
                save_profit.append(profit)
            y = np.array(save_profit)
            return y
        y = calculate_y(x)
        save_index = 0
        previous = 0
        for index,y_ in enumerate(y):
            if y_ < 0 and previous > 0 :
                save_index = index
                break
            if y_ > 0 and previous < 0 :
                save_index = index
                break
            previous = y_
        
        breakeven_price = x[save_index]
        max_loss = min(y)
        levels = []

        text1 = 'breakeven at x = '+ str(round_it(breakeven_price)) + '; ' +'max loss is '+ str(round_it(max_loss))+' per contract'
        fig,ax = plt.subplots()
        ax.plot(x,y)
        ax.set_xlabel('Price of underlying')
        ax.set_ylabel('Profit')
        ax.set_title(text1)
        ax.grid()
        try:
            for index,level in enumerate(self.levels):
                level_profit = round_it(calculate_y(level)[0])
                text3 = '+'+str(level_profit) if level_profit>0 else str(level_profit)
                ax.text(level,sum(ax.get_ylim())/2,text3,fontsize=20, color='red' if level_profit<=0 else 'green')
                levels.append(calculate_y(level)[0])
                ax.axvline(level,c='red' if level_profit<=0 else 'green',ls='--')
        except:
            pass
        file_name = str(self.option_name)+"_"+str(random.randint(0,10000))+'.png'
        plt.savefig(file_name)
        return file_name

def get_option_list():
    mark_price_data = 'https://eapi.binance.com/eapi/v1/mark'
    response = requests.get(mark_price_data)
    json_file = response.json()
    option_data = pd.DataFrame(json_file)
    dict_ = {'ticker':[],'is_call':[],'K':[],'expiration':[]} 
    def get_timestamp(str_):
        date_ = str_
        return pd.Timestamp(year=2000+int(date_[0:2]), month=int(date_[2:4]), day=int(date_[4:6]), hour=8, tz='UTC')
    for i in range(len(option_data['symbol'])):
        dict_['ticker'].append(option_data['symbol'][i][0:3])
        dict_['is_call'].append(option_data['symbol'][i][-1:])
        dict_['K'].append(option_data['symbol'][i][11:-2])
        dict_['expiration'].append(get_timestamp(option_data['symbol'][i][4:-6].replace('-','')))
    joined = pd.DataFrame(dict_).join(option_data) #join option data
    return joined

def get_properties(joined, option_name):
    line = joined [joined['symbol']==option_name]
    parse_crypto=option_name[0:3]
    K = int(line.iloc[0,2])
    T = (line.iloc[0,3] - pd.Timestamp.now(tz='UTC')) / np.timedelta64(1, 'D')
    cost_per_contract = float(line.iloc[0,8])
    num_of_contracts = 1
    is_call = line.iloc[0,1] == "C"
    return (K,T, cost_per_contract,num_of_contracts,is_call,parse_crypto, option_name)

def typingeffect(string):
    for i in string:
        if i!=" ":
            print(i, end="", flush=True)
            time.sleep(0.02)
        else:
            print(i, end="", flush=True)
            time.sleep(0.05)            

if __name__ == '__main__':
    typingeffect('Would you like to get a list of options from Binance REST API as csv file? (yes/no): \n')  
    list_of_option_request = input()
    if list_of_option_request=='yes':
        data = get_option_list()
        today = pd.Timestamp.now(tz='UTC')
        file_name = 'List of options '+str(today.year)+'_'+str(today.month)+"_"+str(today.day)+'.csv'
        data.to_csv(file_name)
        typingeffect(f'Please check out the root folder, file name is: {file_name}')
    elif list_of_option_request=='no':
        typingeffect('Would you like to get a profit diagram for a particular option? (yes/no): \n')
        diagram_request = input()
        if diagram_request == 'yes':
            typingeffect('Please enter the option name (I can not parse brackets): \n')
            option_name = input()
            time.sleep(0.5)
            typingeffect('Your chart is almost ready...')
            time.sleep(0.5)
            typingeffect('\nWould you like to draw some price levels (eg support/resistance) on your profit diagram? \n(if so, please use commas,if not, just leave it empty)\n')
            levels = input()            
            if len(levels)!=0:
                levels = [float(i) for i in levels.split(",")]
            data = get_option_list()
            try:
                name_of_the_fle = Profit(*get_properties(data, option_name)).profit(levels=levels)
                typingeffect(f'Please check out the root folder, the file name is: {name_of_the_fle}')
                time.sleep(1)
            except:
                typingeffect('Oopps! Something wrong.')
                time.sleep(1)
        else:
            typingeffect('Okay, goodbye!')
            time.sleep(1)
    
    else:
        typingeffect('Oopps! Something wrong.')
        time.sleep(1)
