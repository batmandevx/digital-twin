"""Indian food library.

carbs: available carbohydrate per typical serving (g).
fast:  fraction of carbohydrate absorbed through the fast gut channel. It is a
       glycaemic-index proxy (fibre, fat and protein slow absorption).
Values are approximations compiled from IFCT-2017 (NIN) and published GI
tables for Indian foods. They are meant for simulation, not dietary advice.
"""

FOODS = {
    # breakfast
    "idli_sambar":      dict(name="Idli + sambar",         hi="इडली सांभर",      carbs=42, fast=0.70, icon="🍥", slot="breakfast"),
    "poha":             dict(name="Poha",                  hi="पोहा",            carbs=46, fast=0.72, icon="🍛", slot="breakfast"),
    "upma":             dict(name="Rava upma",             hi="उपमा",            carbs=40, fast=0.66, icon="🍛", slot="breakfast"),
    "aloo_paratha":     dict(name="Aloo paratha + curd",   hi="आलू पराठा",       carbs=58, fast=0.62, icon="🫓", slot="breakfast"),
    "masala_dosa":      dict(name="Masala dosa",           hi="मसाला डोसा",      carbs=62, fast=0.74, icon="🌯", slot="breakfast"),
    "oats_milk":        dict(name="Oats with milk",        hi="ओट्स",            carbs=35, fast=0.45, icon="🥣", slot="breakfast"),
    "besan_chilla":     dict(name="Besan chilla",          hi="बेसन चीला",       carbs=24, fast=0.35, icon="🥞", slot="breakfast"),
    "bread_omelette":   dict(name="Bread omelette",        hi="ब्रेड ऑमलेट",     carbs=30, fast=0.70, icon="🍳", slot="breakfast"),
    # lunch / dinner
    "rice_dal_thali":   dict(name="Rice-dal thali",        hi="चावल दाल थाली",   carbs=88, fast=0.80, icon="🍚", slot="meal"),
    "rice_sambar_rasam":dict(name="Rice, sambar & rasam",  hi="सांभर चावल",      carbs=92, fast=0.82, icon="🍚", slot="meal"),
    "roti_dal_sabzi":   dict(name="Roti, dal & sabzi",     hi="रोटी दाल सब्ज़ी",  carbs=62, fast=0.58, icon="🫓", slot="meal"),
    "millet_roti_sabzi":dict(name="Jowar/ragi roti + sabzi",hi="ज्वार रोटी",     carbs=50, fast=0.38, icon="🌾", slot="meal"),
    "brown_rice_rajma": dict(name="Brown rice + rajma",    hi="ब्राउन राइस राजमा",carbs=70, fast=0.48, icon="🍲", slot="meal"),
    "chicken_biryani":  dict(name="Chicken biryani",       hi="चिकन बिरयानी",    carbs=95, fast=0.76, icon="🍗", slot="meal"),
    "fish_rice":        dict(name="Fish curry + rice",     hi="माछ भात",         carbs=85, fast=0.78, icon="🐟", slot="meal"),
    "chole_bhature":    dict(name="Chole bhature",         hi="छोले भटूरे",      carbs=98, fast=0.72, icon="🫓", slot="meal"),
    "khichdi":          dict(name="Moong dal khichdi",     hi="खिचड़ी",          carbs=56, fast=0.58, icon="🥘", slot="meal"),
    "paneer_roti":      dict(name="Paneer sabzi + roti",   hi="पनीर रोटी",       carbs=54, fast=0.52, icon="🧀", slot="meal"),
    # snacks & beverages
    "chai_biscuit":     dict(name="Chai + biscuits",       hi="चाय बिस्कुट",     carbs=26, fast=0.92, icon="☕", slot="snack"),
    "samosa_chai":      dict(name="Samosa + chai",         hi="समोसा चाय",       carbs=42, fast=0.84, icon="🥟", slot="snack"),
    "banana":           dict(name="Banana",                hi="केला",            carbs=26, fast=0.62, icon="🍌", slot="snack"),
    "sprouts_chaat":    dict(name="Sprouts chaat",         hi="अंकुरित चाट",     carbs=20, fast=0.30, icon="🥗", slot="snack"),
    "roasted_chana":    dict(name="Roasted chana",         hi="भुना चना",        carbs=16, fast=0.28, icon="🥜", slot="snack"),
    # festival & fasting foods (Navratri)
    "sabudana_khichdi": dict(name="Sabudana khichdi",      hi="साबूदाना खिचड़ी", carbs=74, fast=0.92, icon="🥣", slot="fast"),
    "kuttu_puri_aloo":  dict(name="Kuttu puri + aloo",     hi="कुट्टू पूरी",     carbs=68, fast=0.74, icon="🫓", slot="fast"),
    "fruit_plate":      dict(name="Fruit plate",           hi="फल",              carbs=34, fast=0.60, icon="🍎", slot="fast"),
    "sweet_lassi":      dict(name="Sweet lassi",           hi="मीठी लस्सी",      carbs=38, fast=0.85, icon="🥛", slot="fast"),
    "mithai":           dict(name="Mithai (sweets)",       hi="मिठाई",           carbs=48, fast=0.95, icon="🍬", slot="fast"),
}

# Swap suggestions used by the What-If lab and patient nudges.
LOW_GI_SWAPS = {
    "rice_dal_thali": "millet_roti_sabzi",
    "rice_sambar_rasam": "brown_rice_rajma",
    "chicken_biryani": "brown_rice_rajma",
    "fish_rice": "brown_rice_rajma",
    "chole_bhature": "roti_dal_sabzi",
    "aloo_paratha": "besan_chilla",
    "masala_dosa": "besan_chilla",
    "poha": "oats_milk",
    "sabudana_khichdi": "fruit_plate",
    "chai_biscuit": "roasted_chana",
    "samosa_chai": "sprouts_chaat",
}
