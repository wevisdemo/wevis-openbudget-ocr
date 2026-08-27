import re

def convert_to_pattern(text: str) -> str:
    pttn_text = re.sub(r"\s", r"\\s\?", text)
    return r"^" + pttn_text

def clean_lgo_name(name: str) -> str:
    name = re.sub(r"([\u0e00-\u0e56])(\u0e4c)([\u0e34-\u0e39])", r"\g<1>\g<3>\g<2>", name)
    name = re.sub(r"(เทศบาล)(ต.{,4}?ล)", r"\g<1>ตำบล", name)
    misorder_name = re.search(r"(.*)((เทศบาล)(ต.{,4}?ล|นคร|เมือง))", name)
    if misorder_name:
        name = re.sub(r"(.*)((เทศบาล)(ต.{,4}?ล|นคร|เมือง))", r"\g<2>\g<1>", name)
    name = re.sub(r"จังหวัด.*", "", name)
    return name
    