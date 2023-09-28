# mouser_api.py>

import requests
import json

#function

mouserPartNumber = '1234'
baseUrl = 'https://api.mouser.com/api/v1.0/search/partnumber'
apiKey = 'b5282dfe-e14f-4bd3-b3cf-2d38e02b3ca8'

url = baseUrl + f'?apiKey={apiKey}'
partSearchOptions = None

body={}
body["SearchByPartRequest"]={}
body["SearchByPartRequest"]['mouserPartNumber'] = mouserPartNumber
body["SearchByPartRequest"]['partSearchOptions'] = partSearchOptions

response = requests.post(url = url, json = body,  headers={'Content-Type': 'application/json'}, timeout = 5)
print(response.json())

test = response.json()

#print(response.text)
#print(dic["SearchResults"]["Parts"][0]["Description"])
#print(dic["SearchResults"]["Parts"][0]["Manufacturer"])
#print(dic["SearchResults"]["Parts"][0]["ManufacturerPartNumber"])
#print(dic["SearchResults"]["Parts"][0]["ProductDetailUrl"])
#print(dic["SearchResults"]["Parts"][0]["DataSheetUrl"])
