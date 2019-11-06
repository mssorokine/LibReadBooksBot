import base64
import json

import requests

import settings

URL = 'https://www.bgoperator.ru/bgmarket/forms?fid=101713843141&__act=q'

HEADERS = {
    'Authorization': f'Basic {settings.BOOK_API_TOKEN}',
    'Content-Type': 'application/json',
}


fields = [
    'id',
    'name',
    'author',
    'isbn_',
    'ean_13',
    'edition',
    'publishyear',
    'cover',
    'age_category',
    'city',
    'weight',
    'text',
    'subtitle',
    'text_full',
    'udc',
    'series',
    'width',
    'thickness',
    'height',
    'contributorstatement',
    'editor',
    'compiler',
    'translator',
    'illustrator',
    'coverimage',
]


fields = ' '.join(fields)
query = 'query($cond: [Condition]!){meta{getSrcObs(typeName: t_2, first: 10 conditions:$cond){edges{node{... on t_2 {%s}}}}}}' % fields


