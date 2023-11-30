# mouser_api.py>

import requests
import json

#function
def ApiSearch(mouser_part_number):
#mouserPartNumber = 'MAX40007AUT+T'
    base_url = 'https://api.mouser.com/api/v1.0/search/partnumber'
    api_key = 'b5282dfe-e14f-4bd3-b3cf-2d38e02b3ca8'

    url = base_url + f'?apiKey={api_key}'
    part_search_options = None

    body = {"SearchByPartRequest": {}}
    body["SearchByPartRequest"]['mouserPartNumber'] = mouser_part_number
    body["SearchByPartRequest"]['partSearchOptions'] = part_search_options

    response = requests.post(url = url, json = body,  headers={'Content-Type': 'application/json'}, timeout = 10)
    return response.json()
    #print(response.text)
    #print(dic["SearchResults"]["Parts"][0]["Description"])
    #print(dic["SearchResults"]["Parts"][0]["Manufacturer"])
    #print(dic["SearchResults"]["Parts"][0]["ManufacturerPartNumber"])
    #print(dic["SearchResults"]["Parts"][0]["ProductDetailUrl"])
    #print(dic["SearchResults"]["Parts"][0]["DataSheetUrl"])
