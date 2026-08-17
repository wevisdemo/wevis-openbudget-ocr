MINISTRY_NAMES = [
    'กระทรวงศึกษาธิการ',
    'กระทรวงพลังงาน',
    'กระทรวงพาณิชย์'
]

BUDGET_TREE_DEFAULT_COLUMNS = [
    'error_message', 'budget_type',
    'name_1','name_2','name_3','name_4','name_5','name_6','name_7','name_8','name_9','name_10','name_11',
    'amount','document','page','fiscal_year','fiscal_year_end'
]

OCR_BLOCK_LIST = "¢£¤¥ฺ"

PREFIX_PATTERNS = [
    # budget plan 7.x
    (r"^7\.(\d+)", 1),
    
    # x.x.x.x
    (r"^(\d+)\.\s?งบ", 1),
    (r"^\d+\.(\d+)\s", 1),
    (r"^\d+\.\d+\.(\d+)\s", 1),
    (r"^\d+\.\d+\.\d+\.(\d+)\s", 1),
    
    # x.x.x)
    (r"^(\d+)\)\s", 1),
    (r"^\d+\.(\d+)\s?\)\s", 1),
    (r"^\d+\.\d+\.(\d+)\s?\)\s", 1),
    (r"^\d+\.\d+\.\d+\.(\d+)\s?\)\s", 1),
    
    # (x.x.x)
    (r"^\((\d+)\)\s", 1),
    (r"^\(\d+\.(\d+)\)\s", 1),
    (r"^\(\d+\.\d+\.(\d+)\)\s", 1),
    (r"^\(\d+\.\d+\.\d+\.(\d+)\)\s", 1),
    
    # x เงิน|ค่าใช้จ่า
    (r"(?<!\d\.)(\d+)\s?(เงิน|ค่า)", 1),

    (r"^(ผลผลิต|โครงการ)\s?\:", None),
    (r"^กิจกรรม", None),
    
    # Fiscal year
    (r"^ปี\s?25\d{2}", None),
    (r"^วงเงิน", None),
    
    # Outside budget
    (r"^เงินนอกงบประมาณ", None)
]