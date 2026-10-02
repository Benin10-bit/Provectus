import unicodedata,re

def normalize(text):
    # NFC preserves compatibility superscripts; never strip mathematical signs or punctuation.
    return re.sub(r'\s+',' ',unicodedata.normalize('NFC',text)).strip()
