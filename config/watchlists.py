"""Comprehensive global watchlist organized by packages.

~5000 symbols across all major markets, sectors, cap sizes, and themes.
Each package can be independently selected for analysis.

yfinance ticker suffixes:
  US: no suffix          UK: .L          Germany: .DE       France: .PA
  Netherlands: .AS       Spain: .MC      Italy: .MI         Switzerland: .SW
  Sweden: .ST            Denmark: .CO    Finland: .HE       Norway: .OL
  Japan: .T              Hong Kong: .HK  Korea: .KS         India: .NS
  Australia: .AX         Taiwan: .TW     Singapore: .SI     Brazil: .SA
  Canada: .TO            South Africa: .JO   Saudi Arabia: .SR   Mexico: .MX
"""

from typing import Dict, List, Tuple


# ══════════════════════════════════════════════════════════════════════
# Package Metadata: name, region, category, description
# ══════════════════════════════════════════════════════════════════════

PACKAGE_META: Dict[str, Dict[str, str]] = {
    # ── US Markets ──
    "us_mega_cap":        {"name": "US Mega Cap",           "region": "US",     "category": "Large Cap",   "description": "Top 50 US companies by market cap"},
    "us_sp500":           {"name": "S&P 500",               "region": "US",     "category": "Large Cap",   "description": "Full S&P 500 index constituents"},
    "us_nasdaq100":       {"name": "NASDAQ 100",            "region": "US",     "category": "Large Cap",   "description": "NASDAQ 100 index members"},
    "us_mid_cap":         {"name": "US Mid Cap",            "region": "US",     "category": "Mid Cap",     "description": "S&P 400 and mid-cap growth stocks"},
    "us_small_cap":       {"name": "US Small Cap",          "region": "US",     "category": "Small Cap",   "description": "Russell 2000 notable and small-cap growth"},
    "us_micro_cap":       {"name": "US Micro Cap",          "region": "US",     "category": "Micro Cap",   "description": "High-risk, high-reward micro caps"},
    "us_dividend":        {"name": "Dividend Aristocrats",  "region": "US",     "category": "Income",      "description": "25+ years of consecutive dividend increases"},
    "us_reits":           {"name": "US REITs",              "region": "US",     "category": "Real Estate",  "description": "Real estate investment trusts"},
    "us_ipos":            {"name": "Recent IPOs",           "region": "US",     "category": "Growth",      "description": "Notable recent IPOs and direct listings"},

    # ── US Sectors ──
    "sector_tech_software":   {"name": "Software & Cloud",      "region": "US", "category": "Sector", "description": "Enterprise software, SaaS, cloud platforms"},
    "sector_semiconductors":  {"name": "Semiconductors",        "region": "US", "category": "Sector", "description": "Chip design, manufacturing, equipment"},
    "sector_cybersecurity":   {"name": "Cybersecurity",         "region": "US", "category": "Sector", "description": "Network security, endpoint, identity, cloud security"},
    "sector_healthcare":      {"name": "Healthcare & Pharma",   "region": "US", "category": "Sector", "description": "Pharma, health insurers, medical devices"},
    "sector_biotech":         {"name": "Biotech & Genomics",    "region": "US", "category": "Sector", "description": "Biotechnology, gene therapy, mRNA, CRISPR"},
    "sector_financials":      {"name": "Financials & Banks",    "region": "US", "category": "Sector", "description": "Banks, insurance, asset managers, exchanges"},
    "sector_fintech":         {"name": "Fintech",               "region": "US", "category": "Sector", "description": "Digital payments, crypto exchanges, neobanks"},
    "sector_energy":          {"name": "Energy (Oil & Gas)",    "region": "US", "category": "Sector", "description": "Oil majors, E&P, oilfield services, midstream"},
    "sector_clean_energy":    {"name": "Clean Energy",          "region": "US", "category": "Sector", "description": "Solar, wind, hydrogen, nuclear, utilities"},
    "sector_industrials":     {"name": "Industrials & Defense",  "region": "US", "category": "Sector", "description": "Aerospace, defense, machinery, transport, logistics"},
    "sector_consumer_disc":   {"name": "Consumer Discretionary", "region": "US", "category": "Sector", "description": "Retail, e-commerce, restaurants, travel, auto"},
    "sector_consumer_staples": {"name": "Consumer Staples",     "region": "US", "category": "Sector", "description": "Food, beverage, household, tobacco, personal care"},
    "sector_materials":       {"name": "Materials & Mining",    "region": "US", "category": "Sector", "description": "Chemicals, metals, mining, paper, packaging"},
    "sector_utilities":       {"name": "Utilities",             "region": "US", "category": "Sector", "description": "Electric, gas, water, multi-utilities"},
    "sector_real_estate":     {"name": "Real Estate",           "region": "US", "category": "Sector", "description": "REITs, real estate services, developers"},
    "sector_comm_services":   {"name": "Communication Services", "region": "US", "category": "Sector", "description": "Media, entertainment, telecom, social, streaming"},
    "sector_auto_ev":         {"name": "Automotive & EV",       "region": "US", "category": "Sector", "description": "Traditional auto, EV makers, EV components"},
    "sector_transportation":  {"name": "Transportation",        "region": "US", "category": "Sector", "description": "Airlines, rails, trucking, shipping, logistics"},

    # ── Europe ──
    "uk_ftse":            {"name": "UK FTSE 100/250",      "region": "Europe", "category": "Large Cap",  "description": "London Stock Exchange major constituents"},
    "europe_germany":     {"name": "Germany DAX/MDAX",     "region": "Europe", "category": "Large Cap",  "description": "XETRA listed German companies"},
    "europe_france":      {"name": "France CAC 40",        "region": "Europe", "category": "Large Cap",  "description": "Euronext Paris major constituents"},
    "europe_switzerland": {"name": "Switzerland SMI",      "region": "Europe", "category": "Large Cap",  "description": "Swiss Market Index constituents"},
    "europe_netherlands": {"name": "Netherlands AEX",      "region": "Europe", "category": "Large Cap",  "description": "Euronext Amsterdam major companies"},
    "europe_nordic":      {"name": "Nordic (Swe/Den/Fin/Nor)", "region": "Europe", "category": "Mixed", "description": "OMX Stockholm, Copenhagen, Helsinki, Oslo"},
    "europe_spain":       {"name": "Spain IBEX 35",        "region": "Europe", "category": "Large Cap",  "description": "Bolsa de Madrid constituents"},
    "europe_italy":       {"name": "Italy FTSE MIB",       "region": "Europe", "category": "Large Cap",  "description": "Borsa Italiana major companies"},
    "europe_belgium_portugal": {"name": "Belgium & Portugal", "region": "Europe", "category": "Mixed", "description": "Euronext Brussels and Lisbon"},
    "europe_austria_ireland":  {"name": "Austria & Ireland",  "region": "Europe", "category": "Mixed", "description": "Vienna and Dublin exchanges"},

    # ── Asia Pacific ──
    "japan":              {"name": "Japan Nikkei/TOPIX",   "region": "Asia",   "category": "Large Cap",  "description": "Tokyo Stock Exchange major companies"},
    "china":              {"name": "China (ADRs + HK)",    "region": "Asia",   "category": "Mixed",      "description": "US-listed ADRs and Hong Kong listed Chinese companies"},
    "hong_kong":          {"name": "Hong Kong",            "region": "Asia",   "category": "Large Cap",  "description": "Hang Seng Index and notable HK stocks"},
    "south_korea":        {"name": "South Korea KOSPI",    "region": "Asia",   "category": "Large Cap",  "description": "Korea Exchange major companies"},
    "india":              {"name": "India NIFTY/ADRs",     "region": "Asia",   "category": "Mixed",      "description": "NSE India top companies and US-listed ADRs"},
    "taiwan":             {"name": "Taiwan TWSE",          "region": "Asia",   "category": "Large Cap",  "description": "Taiwan Stock Exchange notable companies"},
    "australia":          {"name": "Australia ASX 200",    "region": "Asia",   "category": "Large Cap",  "description": "Australian Securities Exchange major companies"},
    "singapore":          {"name": "Singapore STI",        "region": "Asia",   "category": "Large Cap",  "description": "Straits Times Index constituents"},
    "asean":              {"name": "ASEAN Markets",        "region": "Asia",   "category": "Mixed",      "description": "Thailand, Malaysia, Indonesia, Philippines, Vietnam"},

    # ── Americas (ex-US) ──
    "canada":             {"name": "Canada TSX 60",        "region": "Americas", "category": "Large Cap", "description": "Toronto Stock Exchange major companies"},
    "brazil":             {"name": "Brazil Ibovespa",      "region": "Americas", "category": "Large Cap", "description": "B3 (Bovespa) major constituents"},
    "mexico":             {"name": "Mexico IPC",           "region": "Americas", "category": "Large Cap", "description": "BMV listed Mexican companies"},
    "latam_other":        {"name": "LatAm Other",          "region": "Americas", "category": "Mixed",     "description": "Chile, Colombia, Argentina, Peru"},

    # ── Middle East & Africa ──
    "middle_east":        {"name": "Middle East",          "region": "MEA",    "category": "Mixed",      "description": "Saudi Arabia, UAE, Qatar, Israel"},
    "south_africa":       {"name": "South Africa JSE",     "region": "MEA",    "category": "Large Cap",  "description": "Johannesburg Stock Exchange top companies"},

    # ── ETFs ──
    "etf_us_index":       {"name": "US Index ETFs",        "region": "Global", "category": "ETF", "description": "S&P 500, NASDAQ, Russell, Dow ETFs"},
    "etf_sector":         {"name": "Sector ETFs",          "region": "Global", "category": "ETF", "description": "SPDR sector, industry, and thematic ETFs"},
    "etf_international":  {"name": "International ETFs",   "region": "Global", "category": "ETF", "description": "Country, region, and emerging market ETFs"},
    "etf_fixed_income":   {"name": "Bond & Fixed Income",  "region": "Global", "category": "ETF", "description": "Treasury, corporate, high yield, muni bond ETFs"},
    "etf_commodity":      {"name": "Commodity ETFs",       "region": "Global", "category": "ETF", "description": "Gold, silver, oil, agriculture, broad commodity ETFs"},
    "etf_thematic":       {"name": "Thematic ETFs",        "region": "Global", "category": "ETF", "description": "AI, robotics, blockchain, clean energy, genomics ETFs"},
    "etf_factor":         {"name": "Factor & Smart Beta",  "region": "Global", "category": "ETF", "description": "Value, growth, momentum, quality, low-vol factor ETFs"},

    # ── Themes ──
    "theme_ai":           {"name": "AI & Machine Learning", "region": "Global", "category": "Theme", "description": "Artificial intelligence, ML infrastructure, AI applications"},
    "theme_ev":           {"name": "EV & Battery",         "region": "Global", "category": "Theme", "description": "Electric vehicles, battery tech, charging infrastructure"},
    "theme_crypto":       {"name": "Crypto & Blockchain",  "region": "Global", "category": "Theme", "description": "Crypto exchanges, miners, blockchain infrastructure"},
    "theme_quantum":      {"name": "Quantum Computing",    "region": "Global", "category": "Theme", "description": "Quantum hardware, software, and services"},
    "theme_space":        {"name": "Space & Satellite",    "region": "Global", "category": "Theme", "description": "Launch providers, satellite operators, space tech"},
    "theme_nuclear":      {"name": "Nuclear & Uranium",    "region": "Global", "category": "Theme", "description": "Nuclear power, uranium mining, SMR technology"},
    "theme_cannabis":     {"name": "Cannabis",             "region": "Global", "category": "Theme", "description": "Cannabis producers, retailers, ancillary services"},
    "theme_robotics":     {"name": "Robotics & Automation", "region": "Global", "category": "Theme", "description": "Industrial robots, surgical robots, drones, automation"},
    "theme_gaming":       {"name": "Gaming & Esports",     "region": "Global", "category": "Theme", "description": "Video game publishers, platforms, esports, VR"},
    "theme_luxury":       {"name": "Luxury & Premium",     "region": "Global", "category": "Theme", "description": "Luxury goods, premium brands, high-end retail"},
    "theme_water":        {"name": "Water & Infrastructure", "region": "Global", "category": "Theme", "description": "Water utilities, treatment, infrastructure"},
    "theme_aging":        {"name": "Aging Population",     "region": "Global", "category": "Theme", "description": "Senior living, home health, medical devices for elderly"},
    "theme_food":         {"name": "Food Innovation",      "region": "Global", "category": "Theme", "description": "Plant-based, precision fermentation, vertical farming, agtech"},
    "theme_infrastructure": {"name": "Infrastructure",     "region": "Global", "category": "Theme", "description": "Construction, engineering, materials, 5G towers"},

    # ── Extended International ──
    "india_extended":     {"name": "India Extended",        "region": "Asia",   "category": "Mixed",      "description": "Nifty Next 50 and BSE Sensex additional stocks"},
    "korea_extended":     {"name": "Korea Extended",        "region": "Asia",   "category": "Mixed",      "description": "KOSPI 200 additional constituents"},
    "australia_extended": {"name": "Australia Extended",    "region": "Asia",   "category": "Mixed",      "description": "ASX 200 additional constituents"},
    "canada_extended":    {"name": "Canada Extended",       "region": "Americas", "category": "Mixed",    "description": "TSX Composite additional stocks"},
    "europe_extended":    {"name": "Europe Extended",       "region": "Europe", "category": "Mixed",      "description": "Poland, Greece, Turkey, Czech, Hungary, Romania"},
    "global_adrs":        {"name": "Global ADRs",           "region": "Global", "category": "ADR",        "description": "Major ADRs trading on US exchanges"},
    "us_spacs_desspacs":  {"name": "SPACs & De-SPACs",      "region": "US",     "category": "Speculative", "description": "Completed SPAC mergers and notable de-SPACs"},
    "us_Russell_1000_add": {"name": "Russell 1000 Add'l",   "region": "US",     "category": "Large Cap",  "description": "Russell 1000 stocks not in S&P 500 / NASDAQ 100"},
    "us_russell2000_broad": {"name": "Russell 2000 Broad",  "region": "US",     "category": "Small Cap",  "description": "Broad Russell 2000 coverage - small caps"},
    "us_otc_notable":     {"name": "OTC Notable",           "region": "Global", "category": "ADR/OTC",    "description": "Notable OTC pink sheets - international companies"},
}


# ══════════════════════════════════════════════════════════════════════
# Watchlist Packages: symbol lists
# ══════════════════════════════════════════════════════════════════════

WATCHLIST_PACKAGES: Dict[str, List[str]] = {

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# US MARKETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"us_mega_cap": [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "TSLA",
    "UNH", "XOM", "LLY", "JPM", "JNJ", "V", "AVGO", "PG", "MA", "HD",
    "MRK", "COST", "ABBV", "CVX", "CRM", "NFLX", "AMD", "PEP", "KO",
    "WMT", "TMO", "ADBE", "CSCO", "ACN", "MCD", "LIN", "ABT", "ORCL",
    "DHR", "TXN", "CMCSA", "PM", "INTC", "INTU", "NOW", "NEE", "GE",
    "CAT", "RTX", "BA", "ISRG", "AMGN",
],

"us_sp500": [
    # Full S&P 500 constituents (~503 symbols)
    "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI",
    "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG",
    "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN",
    "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH",
    "APTV", "ARE", "ATO", "ATVI", "AVB", "AVTR", "AVY", "AWK", "AXP", "AZO",
    "BA", "BAC", "BAX", "BBWI", "BDX", "BEN", "BF-B", "BG", "BIIB", "BIO",
    "BK", "BKNG", "BKR", "BLDR", "BMY", "BR", "BRK-B", "BRO", "BSX", "BWA",
    "BX", "BXP", "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE",
    "CCI", "CCL", "CDAY", "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD",
    "CHRW", "CHTR", "CI", "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG",
    "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY",
    "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP", "CSX", "CTAS", "CTLT",
    "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D", "DAL", "DAY", "DD",
    "DE", "DECK", "DFS", "DG", "DGX", "DHI", "DHR", "DIS", "DLTR", "DOV",
    "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "DXCM", "EA", "EBAY",
    "ECL", "ED", "EFX", "EIX", "EL", "EMN", "EMR", "ENPH", "EOG", "EPAM",
    "EQIX", "EQR", "EQT", "ES", "ESS", "ETN", "ETR", "EVRG", "EW", "EXC",
    "EXPD", "EXPE", "EXR", "F", "FANG", "FAST", "FBHS", "FCX", "FDS", "FDX",
    "FE", "FFIV", "FI", "FICO", "FIS", "FISV", "FITB", "FMC", "FOX", "FOXA",
    "FRT", "FSLR", "FTNT", "FTV", "GD", "GDDY", "GE", "GEHC", "GEN", "GEV",
    "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL", "GPC", "GPN",
    "GRMN", "GS", "GWW", "HAL", "HAS", "HBAN", "HCA", "HD", "HOLX", "HON",
    "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM", "IBM",
    "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH", "IP",
    "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J", "JBHT",
    "JBL", "JCI", "JKHY", "JNJ", "JNPR", "JPM", "K", "KDP", "KEY", "KEYS",
    "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI", "KMX", "KO", "KR", "KVUE",
    "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LRCX", "LULU",
    "LUV", "LVS", "LW", "LYB", "LYV", "MA", "MAA", "MAR", "MAS", "MCD",
    "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET", "META", "MGM", "MHK", "MKC",
    "MKTX", "MLM", "MMC", "MMM", "MNST", "MO", "MOH", "MOS", "MPC", "MPWR",
    "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTB", "MTCH", "MTD",
    "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC",
    "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWL", "NWS",
    "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE", "OMC", "ON", "ORCL", "ORLY",
    "OTIS", "OXY", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE",
    "PFG", "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PM", "PNC", "PNR",
    "PNW", "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PVH",
    "PWR", "PXD", "PYPL", "QCOM", "QRVO", "RCL", "REG", "REGN", "RF", "RJF",
    "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", "SBAC",
    "SBUX", "SCHW", "SEE", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO",
    "SOLV", "SPG", "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK",
    "SWKS", "SYF", "SYK", "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL",
    "TER", "TFC", "TFX", "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB",
    "TROW", "TRV", "TSCO", "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL",
    "UAL", "UBER", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
    "V", "VICI", "VLO", "VLTO", "VMC", "VRSN", "VRTX", "VST", "VTR", "VTRS",
    "VZ", "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR",
    "WM", "WMB", "WMT", "WRB", "WRK", "WST", "WTW", "WY", "WYNN", "XEL",
    "XOM", "XYL", "YUM", "ZBH", "ZBRA", "ZTS",
],

"us_nasdaq100": [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "ARM", "ASML", "AVGO", "AZN", "BIIB", "BKNG", "BKR", "CDNS",
    "CDW", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO", "CSGP", "CTAS",
    "CTSH", "DASH", "DDOG", "DLTR", "DXCM", "EA", "EBAY", "ENPH", "EXC", "FANG",
    "FAST", "FTNT", "GEHC", "GFS", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "ILMN",
    "INTC", "INTU", "ISRG", "KDP", "KHC", "KLAC", "LRCX", "LULU", "MAR", "MCHP",
    "MDB", "MDLZ", "MELI", "META", "MNST", "MRNA", "MRVL", "MSFT", "MU", "NFLX",
    "NVDA", "NXPI", "ODFL", "ON", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP",
    "PYPL", "QCOM", "REGN", "RIVN", "ROST", "SBUX", "SMCI", "SNPS", "SPLK", "TEAM",
    "TMUS", "TSLA", "TTD", "TTWO", "TXN", "VRSK", "VRTX", "WBA", "WDAY", "XEL", "ZS",
],

"us_mid_cap": [
    # S&P 400 / Mid Cap Growth (~200 symbols)
    "ACHC", "ACM", "ACLS", "AGCO", "AIT", "ALK", "ALLY", "AMKR", "AOS", "ARWR",
    "ATI", "AZEK", "BALY", "BC", "BFAM", "BJ", "BRBR", "BURL", "BWA", "CACC",
    "CACI", "CARG", "CARS", "CASY", "CBT", "CBSH", "CEIX", "CHE", "CHDN", "CHH",
    "CIEN", "CLF", "CLH", "CMC", "CNA", "CNM", "CNX", "COLM", "COOP", "CORT",
    "CRC", "CRI", "CRS", "CRSP", "CW", "CWST", "CWK", "DCI", "DINO", "DNLI",
    "DTM", "DXC", "EAT", "EEFT", "EGP", "EHC", "ENSG", "ENS", "ENTG", "ESAB",
    "ESI", "ETSY", "EVR", "EXP", "EXEL", "FAF", "FHI", "FIX", "FLO", "FLS",
    "FNB", "FND", "FROG", "FSS", "GATX", "GKOS", "GGG", "GHC", "GLOB", "GLPI",
    "GPK", "GTES", "GNTX", "G", "GWRE", "HAE", "HGV", "HLI", "HLF", "HLNE",
    "HP", "HQY", "HR", "HRI", "HRB", "HUBG", "HWC", "IART", "IBP", "ICL",
    "ICLR", "IDCC", "IDA", "INGR", "INST", "ITCI", "ITT", "JBGS", "JBSS", "JEF",
    "JHG", "JLL", "JWN", "KBR", "KEX", "KNX", "KNTK", "KRG", "KRC", "LANC",
    "LBRDK", "LEA", "LFUS", "LITE", "LNTH", "LPLA", "LSTR", "LTH", "MANH", "MAN",
    "MASI", "MAT", "MATX", "MBC", "MBUU", "MC", "MCW", "MDU", "MDRX", "MEDP",
    "MGNI", "MIDD", "MKSI", "MNKD", "MOD", "MPW", "MRVI", "MSTR", "MTH", "MTN",
    "MTSI", "MUR", "MUSA", "NATI", "NEU", "NJR", "NMIH", "NNI", "NOG", "NOVT",
    "NSIT", "NSP", "NTCT", "NVAX", "NVT", "OLED", "OMCL", "ORA", "OSK", "OTTR",
    "OVV", "PAGA", "PAG", "PATK", "PBF", "PCH", "PCOR", "PCTY", "PEN", "PERI",
    "PI", "PINC", "PIPR", "PLNT", "PNM", "POR", "POST", "POWL", "PR", "PRGS",
    "PRI", "PRM", "PRTA", "PSN", "PVH", "RBC", "RGA", "RH", "RHP", "RIG",
    # Additional mid-cap expansion (~200 more)
    "ACIW", "ALKS", "AMED", "AMPH", "ARI", "AVNT", "AXTA", "BANF", "BCRX",
    "BDC", "BERY", "BHF", "BRKL", "BRKS", "BWXT", "CBZ", "CIGI", "CNMD",
    "COKE", "COLM", "COHR", "CRVL", "CSGS", "CVNA", "DAN", "DCI", "DEI",
    "DOC", "DKS", "EGP", "ELAN", "ELF", "ENTA", "ESAB", "EVR", "EXP",
    "FAF", "FHI", "FHN", "FIVE", "FLO", "FLS", "FLR", "FNB", "FOXF",
    "FSS", "FYBR", "GATX", "GGG", "GH", "GLOB", "GLPI", "GME", "GO",
    "GPK", "GTES", "HAYW", "HEES", "HLI", "HLF", "HP", "HQY", "HRI",
    "HRB", "HUBG", "HWC", "IART", "IBP", "ICLR", "IDCC", "IDA", "INST",
    "ITCI", "ITT", "JEF", "JHG", "JLL", "JWN", "KEX", "KNTK", "KRC",
    "LANC", "LEA", "LFUS", "LGIH", "LITE", "LNTH", "LSTR", "MAT", "MATX",
    "MBUU", "MEDP", "MGNI", "MIDD", "MKSI", "MOD", "MUR", "MUSA", "NEU",
    "NJR", "NNI", "NSP", "NTCT", "OLED", "OMCL", "ORA", "OSK", "OTTR",
    "PAG", "PATK", "PBF", "PCTY", "PEN", "PI", "PINC", "PIPR", "PLNT",
    "POR", "POST", "PRM", "PSN", "RGEN", "RGLD", "RPM", "RXO", "SAM",
    "SCI", "SF", "SIGI", "SITE", "SLAB", "SNV", "SON", "SPSC", "SPR",
    "SSD", "STRA", "TDC", "TENB", "THS", "THO", "TMHC", "TREX", "TTC",
    "TXRH", "UFPI", "USM", "UTHR", "VC", "VCEL", "VCTR", "VNT", "VRNS",
    "VRRM", "VVV", "WAL", "WDFC", "WEX", "WING", "WK", "WSO", "WTS",
    "XRAY", "YEXT", "ZWS", "ACM", "AGR", "ALE", "ALGM", "ALIT", "AMBA",
    "AMN", "AMSC", "ANF", "APAM", "ARES", "ARHS", "ARMK", "ARNC", "ARW",
    "ASND", "ASTE", "ATKR", "AUB", "AVID", "AX", "AYI", "AZEK", "BCPC",
    "BFAM", "BGS", "BHC", "BOOT", "BOX", "BRBR", "BRKR", "BURL", "BWA",
    "CACC", "CACI", "CARG", "CARS", "CASY", "CBT", "CBSH", "CEIX", "CHE",
    "CHDN", "CHH", "CIEN", "CLF", "CLH", "CMC", "CNA", "CNM", "CNX",
    "COOP", "CRC", "CRI", "CRS", "CW", "CWST", "CWK", "DINO", "DTM",
    "DXC", "EAT", "EEFT", "EHC", "ENS", "ENTG", "ETSY", "GGG", "GKOS",
    "GHC", "GWRE", "HAE", "HGV", "HLNE", "HR", "HUBG", "IART", "INGR",
    "ITT", "JBGS", "KBR", "KNX", "LANC", "LBRDK", "LPLA", "LTH", "MANH",
    "MAN", "MASI", "MBC", "MCW", "MDU", "MDRX", "MNKD", "MPW", "MRVI",
    "MSTR", "MTH", "MTN", "MTSI", "NATI", "NOVT", "NSIT", "NVAX", "NVT",
],

"us_small_cap": [
    # Russell 2000 notable / Small Cap Growth (~300+ symbols)
    "ABUS", "ACAD", "ACHR", "ACVA", "ADMA", "ADPT", "ADTN", "AGEN", "AGIO", "AIRS",
    "ALGT", "ALKT", "ALLO", "ALRM", "ALTR", "AMAG", "AMPH", "AMPL", "AMRC", "AMSF",
    "AMWD", "ANDE", "ANIP", "AORT", "APGE", "APLS", "APPF", "APPS", "ARAV", "ARCB",
    "ARCT", "ARDX", "ARIS", "ARLO", "ARNA", "AROC", "ARRY", "ARVN", "ASAN", "ASND",
    "ASTE", "ATKR", "ATRC", "AVAV", "AVPT", "AVXL", "AXNX", "AZTA", "BAND", "BBIO",
    "BCOV", "BCPC", "BEAM", "BHF", "BILL", "BKE", "BL", "BLKB", "BMBL", "BMRN",
    "BOOT", "BOX", "BRCC", "BRKR", "BRZE", "BTDR", "BTU", "CALM", "CALX", "CASA",
    "CATY", "CCRN", "CCSI", "CDMO", "CECO", "CELH", "CERT", "CFR", "CG", "CHGG",
    "CHRD", "CHRS", "CLBK", "CLDX", "CLSK", "CLVT", "CMPR", "CNMD", "CNXC", "CNXN",
    "CODA", "COHU", "COLL", "COMM", "COMP", "CORT", "CPK", "CPRX", "CRBG", "CRDO",
    "CRGY", "CRK", "CROX", "CRVL", "CSTM", "CSWI", "CURV", "CVBF", "CVLT", "CYBR",
    "CYTK", "CZFS", "DBRG", "DCGO", "DDS", "DERM", "DFH", "DGII", "DIOD", "DIS",
    "DJT", "DKS", "DLTH", "DMRC", "DNOW", "DOCN", "DOMO", "DOOR", "DORM", "DOX",
    "DSGX", "DSPG", "DUOL", "DV", "DY", "EAR", "EBON", "ECPG", "EFSC", "EIG",
    "ELAN", "ELBM", "ELF", "ELTK", "ELVN", "EME", "EPC", "EPRT", "ERAS", "ESTE",
    "ETRN", "EVBG", "EVER", "EWTX", "EXAI", "EXPI", "FARO", "FATE", "FCEL", "FIVN",
    "FIZZ", "FLGT", "FLIC", "FLNC", "FLWS", "FN", "FORM", "FOXF", "FREY", "FRGE",
    "FRPT", "FRSH", "FTCI", "FTRE", "FTSM", "FULC", "GBCI", "GBTG", "GCT", "GDRX",
    "GEOS", "GFF", "GH", "GIII", "GLBE", "GLNG", "GMS", "GNRC", "GO", "GOGL",
    "GOSS", "GRND", "GSHD", "GTLB", "GYRE", "HALO", "HAYW", "HEES", "HGV", "HIMS",
    "HL", "HLLY", "HLX", "HMST", "HNI", "HOLI", "HOOD", "HUBG", "HUN", "HUT",
    "HZNP", "IAC", "IBRX", "ICFI", "ICHR", "IDYA", "IESC", "IIPR", "IMNM", "IMVT",
    "INBX", "INFN", "INMD", "INNV", "INSP", "INTA", "IOSP", "IONQ", "IRTC", "ISEE",
    "IVA", "JBT", "JJSF", "JOBY", "JUST", "KALU", "KAR", "KLIC", "KNSA", "KOD",
    "KREF", "KROS", "KTB", "KTOS", "KVYO", "LBRT", "LCID", "LFST", "LGIH", "LILM",
    "LIVN", "LKFN", "LMND", "LNSR", "LOAR", "LOVE", "LQDA", "LRMR", "LZ", "MARA",
    "MATW", "MAX", "MBC", "MBUU", "MCFT", "MCY", "ME", "MGEE", "MGY", "MIRM",
    "MIR", "MITK", "MLKN", "MNDY", "MRCY", "MRSN", "MSGE", "MSGS", "MTX", "MWA",
    "MYGN", "NABL", "NARI", "NBTB", "NCNO", "NKTR", "NMRK", "NOVA", "NTLA", "NUVB",
    "NVCR", "NYAX", "OFIX", "OGS", "OLPX", "ONTO", "OPCH", "OUST", "OVIC", "PAYO",
    # Additional small-cap expansion (~300 more)
    "AADI", "AAOI", "AAWW", "ABG", "ACA", "ACRE", "AEHR", "AEIS", "AFCG", "AGYS",
    "AHCO", "AHH", "AIN", "AIRC", "AKR", "ALGM", "ALT", "ALTO", "ALVO", "AMBC",
    "AMEH", "AMK", "AMRK", "AMRX", "AMSWA", "ANAB", "ANDE", "ANGI", "ANGO", "ANIK",
    "APA", "APAM", "APLE", "APOG", "AQST", "ARCE", "ARHS", "ARKO", "ARNC", "AROC",
    "ARRY", "ARTNA", "ASGN", "ASUR", "ATEC", "ATEN", "ATER", "ATEX", "ATGE", "ATNI",
    "ATRA", "ATSG", "AVAL", "AVDL", "AVDX", "AVES", "AVNS", "AVPT", "AVTA", "AVXL",
    "AX", "AXGN", "AXL", "AXNX", "AY", "AYI", "AZEK", "AZPN", "AZZ", "BALY",
    "BANR", "BBCP", "BBDC", "BCBP", "BCO", "BDTX", "BFS", "BGS", "BHE", "BHVN",
    "BKD", "BKH", "BLBD", "BLFS", "BLMN", "BLUE", "BNL", "BOISE", "BPMC", "BPOP",
    "BPRN", "BRC", "BRG", "BRKL", "BRX", "BSIG", "BTG", "BUR", "BVH", "BVS",
    "BYRN", "CAKE", "CALX", "CAMP", "CARG", "CARS", "CASA", "CATO", "CATY", "CBAN",
    "CBRL", "CBU", "CBZ", "CCS", "CCSI", "CDLX", "CDMO", "CECO", "CENX", "CERS",
    "CFLT", "CFFN", "CGC", "CGNX", "CHCO", "CHCT", "CHGG", "CIGI", "CIVB", "CLDT",
    "CLDX", "CLFD", "CLNE", "CLPT", "CLSK", "CLVS", "CMBM", "CMCO", "CMD", "CMLS",
    "CMPR", "CMRE", "CMP", "CNDT", "CNOB", "CNSL", "COGT", "COHU", "COLL", "COMP",
    "CONN", "COOP", "CORZ", "COUR", "COWN", "CPBI", "CPF", "CPK", "CPRX", "CRBG",
    "CRDO", "CRGY", "CRK", "CRMD", "CRNC", "CRS", "CRVL", "CRVS", "CSQ", "CSTL",
    "CSTM", "CSWI", "CTBI", "CTO", "CTS", "CUBI", "CURV", "CVCO", "CVGI", "CVLT",
    "CWEN", "CWH", "CWST", "CWT", "CXM", "CZFS", "DAIO", "DAR", "DAVA", "DBD",
    "DBRG", "DCGO", "DDD", "DDS", "DERM", "DFH", "DGII", "DIOD", "DJT", "DLHC",
    "DLX", "DMRC", "DNOW", "DNUT", "DOCN", "DOMO", "DOOR", "DORM", "DOX", "DRVN",
    "DSGX", "DVAX", "DV", "DY", "DXPE", "EARN", "EBON", "ECPG", "EFSC", "ELME",
    "ELTK", "ELVN", "EME", "ENTA", "EPC", "EPRT", "ERAS", "ERII", "ESAB", "ESGR",
    "ESTE", "ETRN", "EVBG", "EVER", "EWTX", "EXAI", "EXLS", "EXPI", "EXPO", "EYE",
    "FARO", "FATE", "FCEL", "FIVN", "FIZZ", "FLGT", "FLIC", "FLNC", "FLWS", "FN",
    "FOLD", "FORM", "FOXF", "FREY", "FRGE", "FRPT", "FRSH", "FTCI", "FTRE", "FULC",
    "FULT", "FUV", "GABC", "GATX", "GBCI", "GBTG", "GCT", "GDRX", "GEOS", "GFF",
    "GIII", "GLBE", "GLNG", "GMS", "GO", "GOGL", "GOSS", "GRND", "GSHD", "GTLS",
    "GYRE", "HALO", "HAYW", "HEES", "HIMS", "HL", "HLLY", "HLX", "HMST", "HNI",
    "HOLI", "HP", "HUBG", "HUN", "HUT", "HZNP", "IAC", "IBRX", "ICFI", "ICHR",
],

"us_micro_cap": [
    # High-risk, speculative micro caps (~100 symbols)
    "ACHR", "AI", "AISP", "ALPP", "AMPX", "APLD", "ARBE", "ARQT", "ASTS", "ASTR",
    "ATOM", "ATUS", "AVIR", "BFRI", "BIGC", "BITF", "BLNK", "BNGO", "BNTC", "BTBT",
    "CANO", "CHPT", "CIFR", "CLNN", "CLOV", "CMPO", "COOK", "CRIS", "CRNC", "DAVE",
    "DNA", "DNUT", "DRAG", "DRCT", "EDIT", "ENVX", "EVGO", "EVLV", "FFIE", "FLNC",
    "FUBO", "GENI", "GEVO", "GLS", "GNPX", "GROM", "GRPN", "GSAT", "HGEN", "HLAH",
    "HYMC", "HYPR", "IMMR", "IMPL", "INVZ", "IQ", "IRBT", "JOBY", "KNDI", "KULR",
    "LAC", "LAZR", "LIDR", "LIFW", "LITM", "LLAP", "LMFA", "LUNR", "MAPS", "MDGL",
    "MEGL", "MGAM", "MNMD", "MRIN", "MVIS", "NKLA", "NN", "NNDM", "ORGN", "OWLT",
    "PAYS", "PLBY", "PLUG", "PRCH", "PRST", "PSTG", "PTGX", "QS", "QUBT", "RCAT",
    "RDW", "REKR", "RGTI", "RIOT", "RIVN", "RKLB", "RVPH", "RXRX", "SATL", "SAVA",
],

"us_dividend": [
    # Dividend Aristocrats - 25+ consecutive years of increases (~65 symbols)
    "ABBV", "ABT", "ADM", "ADP", "AFL", "AOS", "APD", "APTV", "ATR", "BDX",
    "BEN", "BF-B", "BRO", "CAH", "CAT", "CB", "CHD", "CINF", "CL", "CLX",
    "CTAS", "CVX", "DOV", "ECL", "ED", "EMR", "ESS", "EXPD", "FRT", "GD",
    "GPC", "GWW", "HRL", "IBM", "ITW", "JNJ", "KMB", "KO", "LEG", "LIN",
    "LOW", "MCD", "MDT", "MKC", "MMM", "NEE", "NUE", "O", "OTIS", "PEP",
    "PG", "PNR", "PPG", "PRGO", "ROP", "SHW", "SJM", "SPGI", "SWK", "SYY",
    "T", "TGT", "TROW", "WBA", "WMT", "XOM",
],

"us_reits": [
    # REITs across all property types (~40 symbols)
    "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "VICI",
    "AVB", "EQR", "MAA", "INVH", "ARE", "UDR", "CPT", "ESS", "SUI", "ELS",
    "IRM", "BXP", "VTR", "HST", "KIM", "REG", "FRT", "PEAK", "HR", "OHI",
    "STAG", "NNN", "STOR", "EPR", "SLG", "MPW", "IIPR", "GLPI", "SBAC", "EXR",
],

"us_ipos": [
    # Notable recent IPOs & direct listings (~30 symbols)
    "ARM", "BIRK", "CART", "CAVA", "DKNG", "DUOL", "FIGS", "HIMS", "IBKR",
    "JOBY", "KVYO", "LFLY", "MNDY", "OWL", "PCOR", "RDDT", "RIVN", "RKLB",
    "SOUN", "TOST", "TPG", "U", "VRT", "VTEX", "ZI", "DOCN", "BRZE", "CWAN",
    "ESTC", "GTLB",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# US SECTORS (detailed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"sector_tech_software": [
    "MSFT", "CRM", "ORCL", "ADBE", "NOW", "INTU", "SNPS", "CDNS", "ANSS", "WDAY",
    "HUBS", "VEEV", "DDOG", "MDB", "NET", "SNOW", "TEAM", "ZS", "PANW", "CRWD",
    "FTNT", "OKTA", "SPLK", "PLTR", "PATH", "BILL", "CFLT", "ESTC", "GTLB", "DOCN",
    "BRZE", "MNDY", "ZI", "PCOR", "MANH", "GWRE", "APPF", "NCNO", "FROG", "BL",
    "S", "TENB", "RPD", "QLYS", "FRSH", "SPSC", "ALTR", "TYL", "PAYC", "PTC",
    "IT", "CSGP", "SSNC", "FDS", "MSCI", "VRSK", "CERT", "BOX", "PRGS", "MDRX",
],

"sector_semiconductors": [
    "NVDA", "AMD", "AVGO", "TSM", "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX",
    "KLAC", "ASML", "ARM", "ON", "ADI", "NXPI", "MCHP", "MRVL", "MPWR", "SWKS",
    "QRVO", "SMCI", "GFS", "ENTG", "AMKR", "CRUS", "LSCC", "MTSI", "ACLS", "COHU",
    "KLIC", "DIOD", "SLAB", "SITM", "WOLF", "AMBA", "PI", "ALGM", "FORM", "RMBS",
],

"sector_cybersecurity": [
    "PANW", "CRWD", "FTNT", "ZS", "S", "TENB", "CYBR", "QLYS", "RPD", "VRNS",
    "FFIV", "NET", "OKTA", "GEN", "NLOK", "MIME", "SAIL", "RDWR", "OSPN", "CALT",
],

"sector_healthcare": [
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "ISRG", "MDT", "SYK", "ELV", "CI", "HCA", "BSX", "EW", "ZBH",
    "BDX", "BAX", "IDXX", "DXCM", "PODD", "HOLX", "ALGN", "RMD", "TFX", "STE",
    "A", "IQV", "CRL", "MTD", "TECH", "DGX", "LH", "COO", "WAT", "HSIC",
    "RVTY", "HUM", "CNC", "MOH", "DVA", "UHS", "EHC", "INCY", "ENSG", "ACHC",
],

"sector_biotech": [
    "MRNA", "BNTX", "REGN", "GILD", "VRTX", "BIIB", "ILMN", "ALNY", "BMRN",
    "SGEN", "EXEL", "INCY", "PCVX", "ARCT", "RVMD", "CRNX", "APLS", "RXRX",
    "CRSP", "NTLA", "BEAM", "EDIT", "NUVB", "VERV", "ARWR", "IONS", "SRPT",
    "ALLO", "KYMR", "FATE", "IOVA", "IMVT", "CYTK", "NKTR", "NVAX", "MDGL",
    "DAWN", "SAVA", "DNLI", "RCKT", "RARE", "RLAY", "TGTX", "BBIO", "AGIO",
    "HALO", "KRYS", "CORT", "LNTH", "AXSM", "PTGX", "GOSS", "KOD", "CPRX",
    "ADPT", "IMCR", "XNCR", "MGNX", "BCOV", "PRTA", "ACAD",
],

"sector_financials": [
    "JPM", "BAC", "WFC", "GS", "MS", "C", "USB", "PNC", "SCHW", "BK",
    "BRK-B", "V", "MA", "AXP", "COF", "MET", "PRU", "AIG", "ALL", "TRV",
    "CB", "AFL", "MMC", "AON", "AJG", "CINF", "BRO", "RJF", "FITB", "CFG",
    "KEY", "HBAN", "MTB", "NTRS", "STT", "ZION", "CMA", "RF", "SIVB", "FRC",
    "FHN", "SNV", "WAL", "IBKR", "MKTX", "CME", "ICE", "CBOE", "NDAQ", "MSCI",
    "SPGI", "MCO", "FDS", "VIRT", "LPLA", "AMG", "TROW", "BEN", "IVZ", "BX",
    "KKR", "APO", "CG", "ARES", "OWL", "HLNE", "EQH", "FNF", "ESNT", "NMIH",
],

"sector_fintech": [
    "COIN", "SQ", "HOOD", "SOFI", "UPST", "AFRM", "NU", "BILL", "PYPL", "FI",
    "GPN", "FIS", "FISV", "DFS", "SYF", "CPAY", "WEX", "EVTC", "RPAY", "PAYO",
    "TOST", "OPEN", "LMND", "ROOT", "DAVE", "MARA", "RIOT", "CLSK", "HUT", "BITF",
],

"sector_energy": [
    "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "MPC", "VLO", "PSX", "PXD",
    "HAL", "DVN", "FANG", "HES", "BKR", "MRO", "APA", "CTRA", "EQT", "OVV",
    "TRGP", "WMB", "KMI", "OKE", "ET", "EPD", "MPLX", "PAA", "DCP", "AM",
    "AR", "RRC", "SWN", "CNX", "NOG", "MTDR", "CRC", "MGY", "CHRD", "PR",
    "PBF", "DINO", "RIG", "HP", "NBR", "PTEN", "LBRT", "NEX", "CHX", "PUMP",
],

"sector_clean_energy": [
    "ENPH", "SEDG", "FSLR", "RUN", "NEE", "AES", "CEG", "VST", "NRG", "NOVA",
    "CSIQ", "JKS", "DQ", "MAXN", "ARRY", "STEM", "BLDP", "PLUG", "FCEL", "BE",
    "CHPT", "EVGO", "BLNK", "CLNE", "GEVO", "SMR", "LEU", "CCJ", "UEC", "NXE",
    "DNN", "UUUU", "BWE", "HASI", "CWEN", "ORA", "AMPS", "FLNC", "ENVX", "QS",
],

"sector_industrials": [
    "CAT", "DE", "HON", "GE", "RTX", "BA", "LMT", "NOC", "GD", "UPS",
    "UNP", "CSX", "FDX", "WM", "RSG", "EMR", "ROK", "ETN", "AME", "ITW",
    "CMI", "PH", "IR", "DOV", "GWW", "FAST", "SNA", "TT", "GNRC", "JCI",
    "OTIS", "CARR", "XYL", "TER", "FTV", "ROP", "NDSN", "PCAR", "AXON",
    "HEI", "TDG", "HWM", "LDOS", "BAH", "CACI", "SAIC", "KBR", "HII",
    "LHX", "TDY", "BWXT", "HXL", "CW", "KTOS", "RKLB", "AVAV", "MRCY",
    "BWA", "LEA", "APTV", "ALV", "MGA", "GNTX", "DAN", "VC", "SWK", "MAS",
],

"sector_consumer_disc": [
    "TSLA", "NKE", "SBUX", "MCD", "TJX", "HD", "LOW", "TGT", "ROST", "CMG",
    "BKNG", "ABNB", "MAR", "HLT", "LVS", "WYNN", "CZR", "MGM", "RCL", "CCL",
    "NCLH", "EXPE", "DPZ", "YUM", "DRI", "EAT", "TXRH", "WING", "CAVA", "SHAK",
    "SHOP", "ETSY", "CHWY", "W", "EBAY", "MELI", "SE", "PDD", "JD", "BABA",
    "F", "GM", "RIVN", "LCID", "LI", "NIO", "XPEV", "DECK", "LULU", "BIRK",
    "CROX", "DKS", "FL", "BBWI", "PVH", "TPR", "RL", "VFC", "GIII", "KTB",
    "ULTA", "EL", "COLM", "SKX", "MNST", "BJ", "FIVE", "DLTR", "DG", "OLLI",
],

"sector_consumer_staples": [
    "PG", "KO", "PEP", "COST", "WMT", "CL", "KMB", "GIS", "K", "HSY",
    "MO", "PM", "STZ", "BF-B", "MNST", "SYY", "ADM", "EL", "KHC", "KDP",
    "CHD", "CLX", "CAG", "CPB", "HRL", "MKC", "SJM", "LW", "TSN", "TAP",
    "KVUE", "BG", "INGR", "DAR", "CALM", "JJSF", "CELH", "FIZZ", "LNDC", "SMPL",
],

"sector_materials": [
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "DOW", "NUE", "STLD",
    "CF", "MOS", "ALB", "BALL", "VMC", "MLM", "IP", "PKG", "CE", "EMN",
    "RPM", "SEE", "SON", "AVY", "ATR", "IFF", "FMC", "HUN", "AXTA", "CBT",
    "OLN", "TROX", "WLKP", "CC", "NEU", "MTX", "WLK", "SMG", "IOSP", "HWKN",
],

"sector_utilities": [
    "NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "WEC", "ED",
    "ES", "AWK", "PEG", "ETR", "FE", "CMS", "AEE", "ATO", "CNP", "NI",
    "EVRG", "PNW", "NRG", "PPL", "DTE", "PCG", "EIX", "OGE", "LNT", "BKH",
],

"sector_real_estate": [
    "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "VICI",
    "AVB", "EQR", "MAA", "INVH", "ARE", "UDR", "CPT", "ESS", "SUI", "ELS",
    "IRM", "BXP", "VTR", "HST", "KIM", "REG", "FRT", "PEAK", "HR", "OHI",
    "STAG", "NNN", "STOR", "EPR", "SLG", "MPW", "IIPR", "GLPI", "SBAC", "EXR",
    "CBRE", "JLL", "CIGI", "RLJ", "AIV", "DEI", "HIW", "CUZ", "JBGS", "PGRE",
],

"sector_comm_services": [
    "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS", "CHTR", "WBD", "PARA", "ROKU",
    "SNAP", "PINS", "TTD", "RBLX", "SPOT", "MTCH", "ZM", "TWLO", "UBER", "LYFT",
    "GOOGL", "META", "EA", "TTWO", "ATVI", "DKNG", "PENN", "RSI", "U", "PUBM",
    "OMC", "IPG", "FOX", "FOXA", "NWS", "NWSA", "IMAX", "LGF-A", "SIRI", "LBRDK",
],

"sector_auto_ev": [
    "TSLA", "F", "GM", "RIVN", "LCID", "LI", "NIO", "XPEV", "FSR", "GOEV",
    "NKLA", "RIDE", "WKHS", "ARVL", "FFIE", "REE", "JOBY", "LILM", "BLBD",
    "APTV", "ALV", "BWA", "LEA", "GNTX", "MGA", "QS", "MVST", "ENVX", "SES",
    "LAC", "ALB", "SQM", "LTHM", "MP", "CHPT", "EVGO", "BLNK", "VLTA", "DCFC",
],

"sector_transportation": [
    "UPS", "FDX", "UNP", "CSX", "NSC", "CP", "JBHT", "ODFL", "XPO", "SAIA",
    "DAL", "UAL", "LUV", "AAL", "ALK", "JBLU", "HA", "SAVE", "RYAAY", "SKYW",
    "UBER", "LYFT", "ABNB", "BKNG", "EXPE", "CHRW", "EXPD", "MATX", "KEX", "HUBG",
    "KNX", "LSTR", "ARCB", "HTLD", "MRTN", "WERN", "SNDR", "GXO", "FWRD", "DSKE",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EUROPE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"uk_ftse": [
    # FTSE 100 + notable FTSE 250 (.L suffix = London)
    "SHEL.L", "BP.L", "AZN.L", "HSBA.L", "ULVR.L", "GSK.L", "RIO.L", "DGE.L",
    "LSEG.L", "REL.L", "BATS.L", "BHP.L", "GLEN.L", "VOD.L", "BA.L", "NG.L",
    "RR.L", "AAL.L", "BT-A.L", "LLOY.L", "BARC.L", "NWG.L", "STAN.L", "HSBC.L",
    "ANTO.L", "CRH.L", "EZJ.L", "EXPN.L", "PRU.L", "LAND.L", "LGEN.L", "SGE.L",
    "AHT.L", "SMDS.L", "TSCO.L", "SBRY.L", "WTB.L", "SSE.L", "CNA.L", "ABF.L",
    "BRBY.L", "IMB.L", "KGF.L", "MKS.L", "MNDI.L", "NXT.L", "PSON.L", "RDSA.L",
    "SKG.L", "SMT.L", "SN.L", "SVT.L", "SMIN.L", "TW.L", "WPP.L", "III.L",
    "AV.L", "BNZL.L", "CPG.L", "CRDA.L", "DCC.L", "ENT.L", "FRES.L", "HLMA.L",
    "IHG.L", "INF.L", "ITRK.L", "JD.L", "JMAT.L", "MGGT.L", "MNDI.L", "PHNX.L",
    "PSN.L", "RKT.L", "RS1.L", "SGRO.L", "SHEL.L", "SHP.L", "DARK.L", "AUTO.L",
    # FTSE 250 notable
    "BME.L", "BDEV.L", "TW.L", "WEIR.L", "WIZZ.L", "DPLM.L", "IGG.L", "IMI.L",
    "JET.L", "LIO.L", "MCRO.L", "MONY.L", "OSB.L", "PAGE.L", "RTO.L", "SHED.L",
    "SPX.L", "STEM.L", "VCT.L", "VSVS.L",
    # More FTSE 250 + AIM notable (~80 more)
    "AAF.L", "AGK.L", "AGR.L", "ANTO.L", "ASC.L", "ASHM.L", "AZN.L",
    "BBOX.L", "BCG.L", "BGEO.L", "BKG.L", "BNZL.L", "BOY.L", "BREE.L",
    "BWY.L", "CAPD.L", "CMCL.L", "CPI.L", "CURY.L", "DPLM.L",
    "ECM.L", "EDIN.L", "FDEV.L", "FDM.L", "FCIT.L", "GAW.L", "GBPG.L",
    "GNS.L", "GOCO.L", "GRG.L", "GROW.L", "GSK.L", "HIK.L", "HOME.L",
    "HSV.L", "HWG.L", "HYVE.L", "IGR.L", "ING.L", "INCH.L", "INF.L",
    "IPO.L", "IPX.L", "JMAT.L", "JMG.L", "JUP.L", "KGF.L", "LGEN.L",
    "MNG.L", "MRO.L", "NFC.L", "NRR.L", "NWG.L", "NXT.L", "OTB.L",
    "PHNX.L", "PIN.L", "PNN.L", "POLY.L", "PSH.L", "QQ.L", "RNWH.L",
    "RSW.L", "SAFE.L", "SDR.L", "SGRO.L", "SHI.L", "SMWH.L", "SNN.L",
    "SSPG.L", "SXS.L", "SYNT.L", "TET.L", "TPK.L", "ULVR.L", "UU.L",
    "VSVS.L", "WINK.L", "WPP.L", "XPS.L",
],

"europe_germany": [
    # DAX 40 + MDAX notable (.DE suffix = XETRA)
    "SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "AIR.DE", "MBG.DE", "BAS.DE", "BMW.DE",
    "MUV2.DE", "IFX.DE", "ADS.DE", "DHL.DE", "SHL.DE", "BEI.DE", "HEN3.DE", "RWE.DE",
    "DB1.DE", "VOW3.DE", "FRE.DE", "1COV.DE", "MTX.DE", "SRT3.DE", "EOAN.DE", "HEI.DE",
    "CON.DE", "PAH3.DE", "VNA.DE", "QIA.DE", "ZAL.DE", "PUM.DE", "ENR.DE", "FME.DE",
    "MRK.DE", "HNR1.DE", "BNR.DE", "DTG.DE", "SY1.DE", "RHM.DE", "DHER.DE", "HAG.DE",
    # MDAX notable
    "TLX.DE", "FPE3.DE", "BOSS.DE", "LEG.DE", "KGX.DE", "AIXA.DE", "EVT.DE", "NDX1.DE",
    "SZG.DE", "GXI.DE", "JEN.DE", "WAF.DE", "AT1.DE", "BC8.DE", "CEC.DE", "HBH.DE",
    "HOT.DE", "KWS.DE", "LXS.DE", "NEM.DE",
],

"europe_france": [
    # CAC 40 + notable (.PA suffix = Euronext Paris)
    "MC.PA", "OR.PA", "TTE.PA", "SAN.PA", "AI.PA", "SU.PA", "BNP.PA", "AIR.PA",
    "KER.PA", "CS.PA", "DSY.PA", "SAF.PA", "BN.PA", "RMS.PA", "DG.PA", "SGO.PA",
    "RI.PA", "HO.PA", "CAP.PA", "VIV.PA", "GLE.PA", "LR.PA", "WLN.PA", "EN.PA",
    "STM.PA", "ORA.PA", "ML.PA", "STLA.PA", "PUB.PA", "VIE.PA", "ERF.PA", "CA.PA",
    "RNO.PA", "ACA.PA", "URW.PA", "ATO.PA", "LHN.PA", "EL.PA", "ENGI.PA", "TKO.PA",
    # SBF 120 notable
    "ALD.PA", "AM.PA", "BIM.PA", "BON.PA", "CGG.PA", "CNP.PA", "COV.PA", "DBV.PA",
    "ELE.PA", "FGR.PA", "GET.PA", "GFC.PA", "ILD.PA", "ING.PA", "NK.PA", "OVH.PA",
],

"europe_switzerland": [
    # SMI + notable (.SW suffix = SIX Swiss Exchange)
    "NESN.SW", "ROG.SW", "NOVN.SW", "ZURN.SW", "UBSG.SW", "ABBN.SW", "CSGN.SW",
    "SREN.SW", "GEBN.SW", "LOGN.SW", "GIVN.SW", "CFR.SW", "SGSN.SW", "SCMN.SW",
    "LONN.SW", "BALN.SW", "ALC.SW", "SIKA.SW", "HOLN.SW", "PGHN.SW",
    "SLHN.SW", "SQN.SW", "SIGN.SW", "STMN.SW", "TEMN.SW", "VACN.SW", "BARN.SW",
    "LISN.SW", "BRKN.SW", "DKSH.SW",
],

"europe_netherlands": [
    # AEX + notable (.AS suffix = Euronext Amsterdam)
    "ASML.AS", "PHIA.AS", "UNA.AS", "PRX.AS", "INGA.AS", "ABN.AS", "HEIA.AS",
    "AD.AS", "RAND.AS", "AKZA.AS", "ASM.AS", "KPN.AS", "WKL.AS", "DSM.AS",
    "NN.AS", "IMCD.AS", "AGN.AS", "BESI.AS", "LIGHT.AS", "URW.AS",
    "AALB.AS", "SBMO.AS", "TKWY.AS", "GLPG.AS", "APAM.AS", "ALLFG.AS", "ADYEN.AS",
    "TOM2.AS", "FLOW.AS", "JDEP.AS",
],

"europe_nordic": [
    # Sweden (.ST suffix = OMX Stockholm)
    "ERIC-B.ST", "ATCO-A.ST", "VOLV-B.ST", "SAND.ST", "ABB.ST", "SEB-A.ST",
    "ASSA-B.ST", "HM-B.ST", "ALFA.ST", "INVE-B.ST", "SKA-B.ST", "SHB-A.ST",
    "HEXA-B.ST", "ESSITY-B.ST", "ELUX-B.ST", "KINV-B.ST", "NIBE-B.ST", "EVO.ST",
    "SINCH.ST", "GETI-B.ST", "SAAB-B.ST", "TELIA.ST", "SWED-A.ST", "BOL.ST",
    "SOBI.ST", "ADDV-B.ST", "CARY.ST", "LIFCO-B.ST", "LUND-B.ST", "SSAB-A.ST",
    # Denmark (.CO suffix = OMX Copenhagen)
    "NOVO-B.CO", "MAERSK-B.CO", "DSV.CO", "VWS.CO", "CARL-B.CO", "PNDORA.CO",
    "COLO-B.CO", "GMAB.CO", "ORSTED.CO", "GN.CO", "NZYM-B.CO", "DEMANT.CO",
    "TRYG.CO", "RBREW.CO", "AMBU-B.CO", "FLS.CO", "ROCK-B.CO", "JYSK.CO",
    "BAVA.CO", "CHR.CO",
    # Finland (.HE suffix = OMX Helsinki)
    "NOKIA.HE", "KNEBV.HE", "SAMPO.HE", "NESTE.HE", "FORTUM.HE", "STERV.HE",
    "UPM.HE", "WRT1V.HE", "METSO.HE", "TYRES.HE", "ELISA.HE", "ORNBV.HE",
    "KESKOB.HE", "CGCBV.HE", "VALMT.HE",
    # Norway (.OL suffix = Oslo)
    "EQNR.OL", "DNB.OL", "MOWI.OL", "TEL.OL", "YAR.OL", "ORK.OL", "AKRBP.OL",
    "SALM.OL", "NHY.OL", "AKER.OL", "TGS.OL", "SUBC.OL", "SCH.OL", "GJF.OL",
    "BWLPG.OL",
],

"europe_spain": [
    # IBEX 35 (.MC suffix = Madrid)
    "SAN.MC", "ITX.MC", "IBE.MC", "BBVA.MC", "TEF.MC", "AMS.MC", "FER.MC",
    "REP.MC", "ACS.MC", "CABK.MC", "ENG.MC", "IAG.MC", "MAP.MC", "RED.MC",
    "GRF.MC", "CLNX.MC", "ELE.MC", "ACX.MC", "MTS.MC", "BKT.MC",
    "FDR.MC", "SGRE.MC", "MEL.MC", "SAB.MC", "LOG.MC", "ALM.MC", "ANA.MC",
    "CIE.MC", "COL.MC", "IDR.MC", "NTGY.MC", "PHM.MC", "ROVI.MC", "SLR.MC",
    "VIS.MC",
],

"europe_italy": [
    # FTSE MIB (.MI suffix = Milan)
    "ISP.MI", "UCG.MI", "ENEL.MI", "ENI.MI", "STLA.MI", "G.MI", "RACE.MI",
    "TEN.MI", "PIRC.MI", "MONC.MI", "PRY.MI", "SRG.MI", "A2A.MI", "BGN.MI",
    "BAMI.MI", "BZU.MI", "CPR.MI", "DIA.MI", "ERG.MI", "HER.MI",
    "IG.MI", "INW.MI", "IPG.MI", "LDO.MI", "MB.MI", "NEXI.MI", "PST.MI",
    "REC.MI", "SPM.MI", "STM.MI", "TIT.MI", "TRN.MI", "UNI.MI", "UNIR.MI",
    "BMED.MI", "FBK.MI", "SFER.MI", "AMP.MI", "CNHI.MI", "IVG.MI",
],

"europe_belgium_portugal": [
    # Belgium (.BR suffix = Euronext Brussels)
    "ABI.BR", "UCB.BR", "SOLB.BR", "AGS.BR", "GBLB.BR", "KBC.BR", "ACKB.BR",
    "COLR.BR", "WDP.BR", "ARGX.BR", "ONTEX.BR", "COFB.BR", "MELE.BR", "TNET.BR",
    "DIE.BR",
    # Portugal (.LS suffix = Euronext Lisbon)
    "GALP.LS", "EDP.LS", "EDPR.LS", "JMT.LS", "SON.LS", "NOS.LS", "BCP.LS",
    "CTT.LS", "ALTR.LS", "SEM.LS", "RENE.LS", "PHR.LS", "NBA.LS", "GLI.LS",
    "COR.LS",
],

"europe_austria_ireland": [
    # Austria (.VI suffix = Vienna)
    "VIG.VI", "OMV.VI", "VOE.VI", "EBS.VI", "RBI.VI", "WIE.VI", "TKA.VI",
    "AND.VI", "BG.VI", "SPI.VI", "IIA.VI", "POST.VI", "FLU.VI", "LNZ.VI",
    "SBO.VI",
    # Ireland (.IR or London-listed)
    "CRH", "SMCI", "RYA.L", "AIB.L", "BKIR.L", "SKG.L", "FBD.L", "KRX.L",
    "GAN.L", "OBG.L", "IPL.L", "KYG.L", "UDG.L", "TOT.L", "INM.L",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASIA PACIFIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"japan": [
    # Nikkei 225 / TOPIX notable (.T suffix = Tokyo)
    "7203.T", "6758.T", "6861.T", "8306.T", "9984.T", "6501.T", "6902.T", "6954.T",
    "7751.T", "8035.T", "4063.T", "4502.T", "4503.T", "4568.T", "6367.T", "7267.T",
    "9983.T", "6098.T", "6981.T", "4661.T", "2914.T", "3382.T", "4543.T", "6273.T",
    "6594.T", "6762.T", "7741.T", "7974.T", "8001.T", "8002.T", "8031.T", "8058.T",
    "8316.T", "8411.T", "8766.T", "8801.T", "9020.T", "9021.T", "9022.T", "9432.T",
    "9433.T", "9434.T", "9613.T", "9735.T", "2802.T", "3407.T", "4004.T", "4005.T",
    "4021.T", "4042.T", "4061.T", "4151.T", "4183.T", "4188.T", "4307.T", "4452.T",
    "4507.T", "4519.T", "4523.T", "4528.T", "4536.T", "4578.T", "4631.T", "4689.T",
    "4704.T", "4755.T", "4901.T", "4911.T", "5019.T", "5020.T", "5108.T", "5201.T",
    "5401.T", "5411.T", "5713.T", "5714.T", "5801.T", "5802.T", "5803.T", "6103.T",
    "6113.T", "6178.T", "6301.T", "6302.T", "6305.T", "6326.T", "6361.T", "6370.T",
    "6471.T", "6473.T", "6479.T", "6503.T", "6506.T", "6645.T", "6674.T", "6701.T",
    "6702.T", "6703.T", "6723.T", "6724.T", "6752.T", "6753.T", "6770.T", "6857.T",
    "6902.T", "6920.T", "6952.T", "6963.T", "6971.T", "6976.T", "7004.T", "7011.T",
    "7012.T", "7013.T", "7180.T", "7186.T", "7201.T", "7202.T", "7205.T", "7211.T",
    "7261.T", "7269.T", "7270.T", "7272.T", "7735.T", "7752.T", "7832.T", "7911.T",
    "7912.T", "7951.T", "8028.T", "8053.T", "8233.T", "8252.T", "8253.T", "8267.T",
    "8303.T", "8304.T", "8308.T", "8309.T", "8354.T", "8591.T", "8601.T", "8604.T",
    "8628.T", "8630.T", "8697.T", "8725.T", "8750.T", "8795.T", "8830.T", "9001.T",
    "9005.T", "9007.T", "9008.T", "9009.T", "9064.T", "9101.T", "9104.T", "9107.T",
    "9142.T", "9143.T", "9147.T", "9202.T", "9301.T", "9501.T", "9502.T", "9503.T",
    "9531.T", "9532.T", "9602.T", "9681.T", "9684.T", "9766.T", "9843.T", "9962.T",
    "9983.T", "9984.T",
    # Additional TOPIX notable (~120 more)
    "2413.T", "2502.T", "2503.T", "2531.T", "2593.T", "2651.T", "2702.T", "2768.T",
    "2801.T", "2871.T", "2875.T", "2897.T", "3086.T", "3088.T", "3092.T", "3099.T",
    "3105.T", "3116.T", "3141.T", "3186.T", "3231.T", "3254.T", "3288.T", "3289.T",
    "3349.T", "3391.T", "3402.T", "3405.T", "3436.T", "3549.T", "3626.T", "3659.T",
    "3668.T", "3738.T", "3765.T", "3769.T", "3774.T", "3861.T", "3923.T", "3941.T",
    "4043.T", "4062.T", "4091.T", "4114.T", "4118.T", "4182.T", "4204.T", "4208.T",
    "4272.T", "4282.T", "4321.T", "4324.T", "4385.T", "4443.T", "4471.T", "4506.T",
    "4516.T", "4521.T", "4527.T", "4530.T", "4534.T", "4544.T", "4553.T", "4571.T",
    "4612.T", "4613.T", "4676.T", "4680.T", "4681.T", "4684.T", "4708.T", "4716.T",
    "4732.T", "4751.T", "4768.T", "4812.T", "4902.T", "4912.T", "4917.T", "4922.T",
    "4927.T", "4967.T", "5002.T", "5101.T", "5105.T", "5110.T", "5214.T", "5232.T",
    "5233.T", "5301.T", "5332.T", "5333.T", "5334.T", "5406.T", "5413.T", "5423.T",
    "5444.T", "5463.T", "5471.T", "5486.T", "5541.T", "5631.T", "5703.T", "5706.T",
    "5707.T", "5711.T", "5715.T", "5741.T", "5901.T", "5929.T", "5938.T", "5943.T",
    "6028.T", "6055.T", "6070.T", "6088.T", "6104.T", "6118.T", "6134.T", "6136.T",
],

"china": [
    # Chinese ADRs (US-listed) + Hong Kong listed
    "BABA", "PDD", "JD", "BIDU", "NIO", "XPEV", "LI", "NTES", "TME", "BILI",
    "IQ", "VIPS", "MNSO", "ZTO", "FUTU", "TIGR", "DIDI", "TAL", "EDU", "GDS",
    "KC", "HTHT", "QFIN", "LX", "FINV", "LKNCY", "YMM", "GOTU", "ZLAB", "BZ",
    # Hong Kong H-shares (.HK)
    "9988.HK", "0700.HK", "3690.HK", "9618.HK", "1810.HK", "2020.HK", "9999.HK",
    "1024.HK", "6618.HK", "2382.HK", "1211.HK", "9626.HK", "0981.HK", "6060.HK",
    "2269.HK", "0241.HK", "3888.HK", "1109.HK", "2015.HK", "9868.HK",
    "2318.HK", "0939.HK", "1398.HK", "3988.HK", "0941.HK", "0883.HK", "0386.HK",
    "0688.HK", "0001.HK", "0002.HK", "0003.HK", "0005.HK", "0011.HK", "0016.HK",
    "0017.HK", "0019.HK", "0027.HK", "0066.HK", "0101.HK", "0175.HK",
    "0267.HK", "0288.HK", "0388.HK", "0669.HK", "0762.HK", "0823.HK", "0857.HK",
    "0868.HK", "0960.HK", "1038.HK", "1044.HK", "1093.HK", "1113.HK", "1177.HK",
],

"hong_kong": [
    # Hang Seng Index + notable
    "0700.HK", "9988.HK", "0005.HK", "1299.HK", "0941.HK", "0388.HK", "2318.HK",
    "0016.HK", "0002.HK", "0001.HK", "0003.HK", "0883.HK", "1038.HK", "0011.HK",
    "0027.HK", "0823.HK", "1113.HK", "0006.HK", "0012.HK", "0066.HK",
    "0175.HK", "0241.HK", "0267.HK", "0288.HK", "0386.HK", "0669.HK", "0688.HK",
    "0762.HK", "0857.HK", "0868.HK", "0960.HK", "0981.HK", "1044.HK", "1093.HK",
    "1109.HK", "1177.HK", "1211.HK", "1398.HK", "1810.HK", "1928.HK",
    "2007.HK", "2020.HK", "2269.HK", "2313.HK", "2382.HK", "2628.HK", "3328.HK",
    "3690.HK", "3988.HK", "6098.HK",
],

"south_korea": [
    # KOSPI 50 + notable (.KS suffix)
    "005930.KS", "000660.KS", "005380.KS", "051910.KS", "006400.KS", "035420.KS",
    "005490.KS", "000270.KS", "055550.KS", "034730.KS", "068270.KS", "028260.KS",
    "012330.KS", "066570.KS", "015760.KS", "003670.KS", "105560.KS", "032830.KS",
    "018260.KS", "096770.KS", "009150.KS", "033780.KS", "003490.KS", "034020.KS",
    "017670.KS", "011200.KS", "010130.KS", "024110.KS", "030200.KS", "036570.KS",
    "086790.KS", "010950.KS", "016360.KS", "010620.KS", "047050.KS", "000810.KS",
    "009540.KS", "018880.KS", "000720.KS", "004020.KS", "090430.KS", "011170.KS",
    "034220.KS", "002790.KS", "021240.KS", "004170.KS", "000100.KS", "011070.KS",
    "007070.KS", "004990.KS",
],

"india": [
    # NIFTY 50 (.NS suffix = NSE) + US-listed ADRs
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "LT.NS", "HCLTECH.NS", "ASIANPAINT.NS", "AXISBANK.NS", "MARUTI.NS",
    "TITAN.NS", "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "POWERGRID.NS", "M&M.NS", "NESTLEIND.NS", "JSWSTEEL.NS",
    "BAJAJFINSV.NS", "ADANIENT.NS", "ONGC.NS", "COALINDIA.NS", "ADANIPORTS.NS",
    "TECHM.NS", "WIPRO.NS", "KOTAKBANK.NS", "DRREDDY.NS", "CIPLA.NS",
    "BRITANNIA.NS", "EICHERMOT.NS", "DIVISLAB.NS", "HEROMOTOCO.NS", "GRASIM.NS",
    "APOLLOHOSP.NS", "BAJAJ-AUTO.NS", "BPCL.NS", "TATACONSUM.NS", "HINDALCO.NS",
    "INDUSINDBK.NS", "SBILIFE.NS", "UPL.NS", "HDFCLIFE.NS", "LTIM.NS",
    # US-listed Indian ADRs
    "INFY", "WIT", "HDB", "IBN", "RDY", "SIFY", "TTM", "VEDL", "WNS",
    "MMYT", "YTRA", "AZRE",
],

"taiwan": [
    # TWSE notable (.TW suffix)
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2881.TW", "2882.TW", "2303.TW",
    "1303.TW", "1301.TW", "2002.TW", "1326.TW", "2412.TW", "5880.TW", "2886.TW",
    "3711.TW", "2891.TW", "2884.TW", "3045.TW", "2357.TW", "6505.TW",
    "2880.TW", "2885.TW", "2892.TW", "1101.TW", "1102.TW", "2395.TW", "3008.TW",
    "2327.TW", "3034.TW", "2382.TW",
],

"australia": [
    # ASX 200 notable (.AX suffix)
    "BHP.AX", "CBA.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX",
    "MQG.AX", "FMG.AX", "TLS.AX", "WOW.AX", "RIO.AX", "GMG.AX", "TCL.AX",
    "WDS.AX", "ALL.AX", "COL.AX", "STO.AX", "QBE.AX", "NCM.AX",
    "AGL.AX", "AMC.AX", "APX.AX", "ASX.AX", "BXB.AX", "CAR.AX", "CPU.AX",
    "DXS.AX", "EDV.AX", "EVN.AX", "GPT.AX", "IAG.AX", "JHX.AX", "LLC.AX",
    "MIN.AX", "MPL.AX", "NEC.AX", "NST.AX", "ORI.AX", "ORG.AX",
    "OSH.AX", "OZL.AX", "REA.AX", "RHC.AX", "S32.AX", "SCG.AX", "SEK.AX",
    "SGP.AX", "SHL.AX", "SUN.AX",
],

"singapore": [
    # STI + notable (.SI suffix)
    "D05.SI", "O39.SI", "U11.SI", "Z74.SI", "BN4.SI", "C6L.SI", "G13.SI",
    "H78.SI", "C09.SI", "C52.SI", "V03.SI", "A17U.SI", "N2IU.SI", "C38U.SI",
    "ME8U.SI", "M44U.SI", "AJBU.SI", "S63.SI", "F34.SI", "BS6.SI",
],

"asean": [
    # Thailand (.BK suffix)
    "PTT.BK", "ADVANC.BK", "SCC.BK", "CPALL.BK", "AOT.BK", "GULF.BK", "KBANK.BK",
    "SCB.BK", "BDMS.BK", "DELTA.BK", "TRUE.BK", "BBL.BK", "PTTGC.BK", "BEM.BK",
    "MINT.BK",
    # Malaysia (.KL suffix)
    "1155.KL", "1295.KL", "5183.KL", "4707.KL", "3182.KL", "1023.KL", "6888.KL",
    "5347.KL", "5225.KL", "4863.KL", "1082.KL", "4715.KL", "5235.KL", "6947.KL",
    "1015.KL",
    # Indonesia (.JK suffix)
    "BBCA.JK", "BBRI.JK", "TLKM.JK", "BMRI.JK", "ASII.JK", "UNVR.JK", "HMSP.JK",
    "BBNI.JK", "ICBP.JK", "INDF.JK", "KLBF.JK", "GGRM.JK", "PGAS.JK", "SMGR.JK",
    "ANTM.JK",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AMERICAS (ex-US)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"canada": [
    # TSX 60 + notable (.TO suffix = Toronto)
    "RY.TO", "TD.TO", "BNS.TO", "BMO.TO", "CM.TO", "MFC.TO", "SLF.TO", "ENB.TO",
    "CNR.TO", "CP.TO", "TRP.TO", "SU.TO", "CNQ.TO", "IMO.TO", "CVE.TO", "HSE.TO",
    "ABX.TO", "FM.TO", "NTR.TO", "POT.TO", "AGI.TO", "K.TO", "FNV.TO", "WPM.TO",
    "SHOP.TO", "CSU.TO", "OTEX.TO", "BB.TO", "LSPD.TO", "GIB-A.TO", "REAL.TO",
    "DOL.TO", "WFG.TO", "L.TO", "MRU.TO", "ATD.TO", "QSR.TO", "RCI-B.TO",
    "BCE.TO", "T.TO", "FFH.TO", "IFC.TO", "POW.TO", "GWO.TO", "NA.TO",
    "TFII.TO", "CAE.TO", "TIH.TO", "BAM-A.TO", "BPY-UN.TO", "CCO.TO",
    "WEED.TO", "TLRY.TO", "ACB.TO", "OGI.TO", "CRON.TO", "CGC.TO",
    "TECK-B.TO", "FTS.TO", "EMA.TO", "AQN.TO",
],

"brazil": [
    # Ibovespa (.SA suffix = B3 São Paulo)
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "B3SA3.SA", "ABEV3.SA",
    "WEGE3.SA", "RENT3.SA", "MGLU3.SA", "LREN3.SA", "BBAS3.SA", "SUZB3.SA",
    "JBSS3.SA", "GGBR4.SA", "HAPV3.SA", "RDOR3.SA", "RAIL3.SA", "VIVT3.SA",
    "TOTS3.SA", "RADL3.SA", "PRIO3.SA", "ENEV3.SA", "EQTL3.SA", "CSAN3.SA",
    "CSNA3.SA", "CMIG4.SA", "BPAC11.SA", "SBSP3.SA", "KLBN11.SA", "ELET3.SA",
    "BRKM5.SA", "CCRO3.SA", "HYPE3.SA", "CPLE6.SA", "ARZZ3.SA", "COGN3.SA",
    "IRBR3.SA", "VIIA3.SA", "ASAI3.SA", "CRFB3.SA",
    # US-listed Brazilian ADRs
    "PBR", "VALE", "ITUB", "BBD", "ABEV", "SBS", "EWZ", "BSBR", "UGP", "SID",
],

"mexico": [
    # IPC (.MX suffix = BMV)
    "AMXL.MX", "WALMEX.MX", "FEMSAUBD.MX", "GFNORTEO.MX", "CEMEXCPO.MX",
    "TLEVISACPO.MX", "GMEXICOB.MX", "GAPB.MX", "BIMBOA.MX", "KOFUBL.MX",
    "ASURB.MX", "OMAB.MX", "MEGACPO.MX", "LABB.MX", "GENTERA.MX",
    "GRUMAB.MX", "PINFRA.MX", "ALSEA.MX", "BOLSAA.MX", "PE&OLES.MX",
],

"latam_other": [
    # Chile, Colombia, Argentina, Peru - US-listed ADRs + local
    "SQM", "BSAC", "ECL", "LTM", "CENCOSUD", "CCU",
    "EC", "AVAL", "CIB", "BHC",
    "YPF", "GGAL", "BMA", "SUPV", "PAM", "TEO", "CAAP", "LOMA", "GLOB",
    "BVN", "SCCO", "BAP", "IFS", "CREDICORP",
    # Local exchanges
    "FALABELLA.SN", "COPEC.SN", "SQM-B.SN", "BSANTANDER.SN", "CENCOSUD.SN",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIDDLE EAST & AFRICA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"middle_east": [
    # Saudi Arabia (.SR suffix = Tadawul)
    "2222.SR", "1180.SR", "2010.SR", "1010.SR", "2350.SR", "1150.SR", "2380.SR",
    "1120.SR", "4013.SR", "2001.SR", "1211.SR", "4001.SR", "4030.SR", "1020.SR",
    "2020.SR",
    # UAE (.AE / London-listed)
    "FAB", "EMAAR", "ADNOC",
    # Israel (US-listed + TASE)
    "NICE", "CHKP", "MNDY", "CYBR", "WIX", "GLBE", "TEVA", "DRIO", "INMD",
    "FVRR", "MGAM", "SEDG", "ENLT", "ESLT", "ICL", "SILC", "MRVL",
    # Qatar
    "QNBK.QA", "IQCD.QA", "QEWS.QA",
],

"south_africa": [
    # JSE Top 40 (.JO suffix = Johannesburg)
    "NPN.JO", "AGL.JO", "BHP.JO", "SOL.JO", "GLN.JO", "FSR.JO", "SBK.JO",
    "ABG.JO", "NED.JO", "MTN.JO", "VOD.JO", "AMS.JO", "SHP.JO", "CFR.JO",
    "BTI.JO", "ANG.JO", "IMP.JO", "SSW.JO", "GFI.JO", "HAR.JO",
    "DSY.JO", "BID.JO", "RMI.JO", "SLM.JO", "MNP.JO", "KIO.JO", "OMU.JO",
    "INP.JO", "REN.JO", "APN.JO",
    # US-listed South African ADRs
    "GOLD", "AU", "HMY", "DRD", "SBSW", "SSL", "NPN", "BTI", "ASAI",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ETFs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"etf_us_index": [
    "SPY", "QQQ", "IWM", "DIA", "MDY", "IJH", "IWB", "VTI", "VOO", "IVV",
    "SPTM", "RSP", "SPYG", "SPYV", "VTV", "VUG", "IWF", "IWD", "IJR", "IWO",
    "VTWO", "VXF", "SCHB", "ITOT", "VV", "MGC", "OEF", "SPLG", "SCHX", "SCHA",
],

"etf_sector": [
    # SPDR Sector ETFs
    "XLK", "XLV", "XLF", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU", "XLRE", "XLC",
    # Industry ETFs
    "SMH", "SOXX", "IGV", "XBI", "IBB", "HACK", "CIBR", "SKYY", "CLOU", "WCLD",
    "ARKK", "ARKG", "ARKF", "ARKW", "ARKQ", "XHB", "ITB", "XRT", "JETS", "PBW",
    "TAN", "FAN", "ICLN", "LIT", "REMX", "URA", "URNM", "WEAT", "CORN", "SOYB",
    "XME", "GDX", "GDXJ", "SLV", "GLD", "AMLP", "XOP", "OIH", "KRE", "KBE",
    "IAI", "IYR", "VNQ", "XLRE", "RWR", "IYT", "IYG", "IYW", "IYH", "IYC",
],

"etf_international": [
    # Regional ETFs
    "EFA", "EEM", "IEMG", "VWO", "VXUS", "VEA", "VGK", "IEUR", "EZU", "HEDJ",
    "FXI", "MCHI", "KWEB", "ASHR", "GXC", "EWJ", "DXJ", "HEWJ", "EWY", "EWT",
    "EWH", "EWS", "INDA", "EPI", "INDY", "EWZ", "EWW", "EWC", "EWA", "EWG",
    "EWQ", "EWP", "EWI", "EWU", "EWL", "EWN", "EWD", "EWK", "ENOR", "EDEN",
    "EIDO", "THD", "EPHE", "VNM", "FM", "FRDM", "KSA", "UAE", "QAT", "FLSA",
    "AFK", "ARGT", "ECH", "GXG", "EPU", "TUR", "GREK", "NORW", "PGAL", "EPOL",
],

"etf_fixed_income": [
    "BND", "AGG", "LQD", "HYG", "JNK", "TLT", "IEF", "SHY", "TIP", "VTIP",
    "VCSH", "VCIT", "VCLT", "MUB", "HYD", "BNDX", "EMB", "LEMB", "IGIB", "USIG",
    "GOVT", "SPTL", "SPTI", "SPTS", "FLOT", "BSV", "BIV", "BLV", "SCHZ", "FBND",
],

"etf_commodity": [
    "GLD", "SLV", "IAU", "SGOL", "PALL", "PPLT", "USO", "BNO", "UNG", "DBA",
    "DBC", "PDBC", "GSG", "COMT", "WEAT", "CORN", "SOYB", "JO", "NIB", "CPER",
    "COPX", "WOOD", "CUT", "LIT", "REMX", "URA", "URNM", "SILJ", "PICK", "SLX",
],

"etf_thematic": [
    # AI & Robotics
    "BOTZ", "ROBO", "IRBO", "AIQQ", "CHAT", "AIPI",
    # Blockchain & Crypto
    "BITO", "BLOK", "BITQ", "DAPP", "IBLC",
    # Clean Energy
    "ICLN", "TAN", "FAN", "PBW", "QCLN", "ACES",
    # Genomics & Biotech
    "ARKG", "GNOM", "IDNA", "XBI",
    # Cybersecurity
    "HACK", "CIBR", "BUG", "IHAK",
    # Space
    "UFO", "ARKX", "ROKT",
    # Cannabis
    "MSOS", "MJ", "YOLO", "THCX",
    # Gaming & Esports
    "ESPO", "NERD", "HERO", "GAMR",
    # Metaverse & VR
    "META", "METV", "VERS",
    # Infrastructure
    "PAVE", "IFRA", "NFRA",
    # Water
    "PHO", "CGW", "FIW", "AQWA",
    # Aging Population
    "OLD", "LNGR",
    # Food Innovation
    "VEGN", "FTEC",
],

"etf_factor": [
    # Factor / Smart Beta ETFs
    "MTUM", "VLUE", "QUAL", "USMV", "SIZE", "MOAT", "DGRW", "DGRO", "SCHD",
    "VIG", "DVY", "HDV", "NOBL", "SDOG", "DIVB", "FVD", "COWZ", "QVAL", "QMOM",
    "JMOM", "JVAL", "JQUA", "JMIN", "JPST", "SPLV", "SPHD", "HDV", "PFF", "PFFD",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THEMES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"theme_ai": [
    "NVDA", "AMD", "GOOGL", "MSFT", "META", "AMZN", "TSM", "AVGO", "ARM",
    "PLTR", "AI", "SMCI", "SNOW", "MDB", "DDOG", "PATH", "CRM", "ORCL",
    "IBM", "SOUN", "BBAI", "UPST", "ASAN", "C3AI", "PRCT", "VEEV", "HUBS",
    "CFLT", "NOW", "ADBE", "INTU", "CDNS", "SNPS", "ANSS", "WDAY",
],

"theme_ev": [
    "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "FSR", "GOEV", "NKLA",
    "WKHS", "RIDE", "ARVL", "FFIE", "REE", "BLBD", "JOBY", "LILM",
    "QS", "MVST", "ENVX", "SES", "CHPT", "EVGO", "BLNK", "VLTA",
    "ALB", "SQM", "LTHM", "MP", "LAC", "PCRFY", "BYDDY", "VWAGY",
    "F", "GM", "STLA", "TM", "HMC", "BMWYY",
],

"theme_crypto": [
    "COIN", "MARA", "RIOT", "HUT", "CLSK", "BITF", "BTBT", "CIFR",
    "MSTR", "SQ", "HOOD", "PYPL", "SOFI", "NU", "SI", "SBNY",
    "GBTC", "BITO", "BLOK", "DAPP",
],

"theme_quantum": [
    "IONQ", "RGTI", "QUBT", "ARQQ", "QBTS",
    "IBM", "GOOGL", "MSFT", "AMZN", "HON",
],

"theme_space": [
    "RKLB", "ASTR", "RDW", "SPCE", "ASTS", "GSAT", "BKSY",
    "LUNR", "MNTS", "VORB", "BA", "LMT", "NOC", "RTX",
    "KTOS", "MAXR", "VSAT", "GILT", "IRDM",
],

"theme_nuclear": [
    "CCJ", "LEU", "SMR", "UEC", "NXE", "DNN", "UUUU", "URG", "URA", "URNM",
    "CEG", "VST", "NRG", "NEE", "BWXT", "GEV", "OKLO",
],

"theme_cannabis": [
    "TLRY", "CGC", "ACB", "CRON", "OGI", "HEXO", "SNDL", "VFF",
    "CURLF", "TCNNF", "GTBIF", "CRLBF", "TRUL",
    "MSOS", "MJ", "YOLO", "THCX",
],

"theme_robotics": [
    "TER", "ISRG", "ROK", "ABB", "FANUY", "IRBT", "BRKS",
    "NVDA", "KTOS", "AVAV", "JOBY", "RKLB", "BOTZ", "ROBO",
    "ZBRA", "GNRC", "AZTA", "MKSI", "NOVT", "CGNX",
],

"theme_gaming": [
    "ATVI", "EA", "TTWO", "NTDOY", "RBLX", "U", "DKNG", "PENN",
    "PLTK", "SE", "SKLZ", "SOGG", "ZYNGA", "GLBE", "CRSR",
    "LOGI", "HEAR", "ESPO", "NERD",
],

"theme_luxury": [
    # Mostly European luxury houses (Paris/Swiss listed + ADRs)
    "MC.PA", "RMS.PA", "KER.PA", "CDI.PA", "EL",
    "MONC.MI", "RACE.MI", "CFR.SW", "BRBY.L",
    "LVMUY", "PPRUY", "HESAY", "CFRUY", "CPRI", "TPR", "RL", "BIRK",
],

"theme_water": [
    "AWK", "WTR", "XYL", "WTRG", "SJW", "CWT", "MSEX", "YORW", "ARTNA",
    "PHO", "CGW", "FIW", "AQWA", "ECL", "NDAQ",
],

"theme_aging": [
    "UNH", "HUM", "ELV", "CI", "CNC", "WELL", "VTR", "OHI", "PEAK", "HR",
    "SYK", "MDT", "ISRG", "ABT", "DXCM", "PODD", "BSX", "EW", "BDX", "ZBH",
    "ENSG", "ACHC", "AMED", "LHCG", "PNTG",
],

"theme_food": [
    "BYND", "TTCF", "VITL", "HAIN", "SMPL", "DAR", "OATLY",
    "DE", "AGCO", "CNHI", "CTVA", "FMC", "MOS", "NTR", "CF",
    "ADM", "BG", "INGR", "TSN", "HRL", "CALM", "SAFM",
    "APPH", "RKDA", "AGFY",
],

"theme_infrastructure": [
    "CAT", "DE", "VMC", "MLM", "URI", "PWR", "EME", "FIX", "MTZ",
    "CRH", "SHW", "PAVE", "IFRA", "NFRA", "BLDR", "AZEK",
    "AMT", "CCI", "SBAC", "EQIX", "DLR",
    "ACM", "J", "WSP", "FLR", "KBR", "AECOM",
],

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADDITIONAL INTERNATIONAL (expanded coverage)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"india_extended": [
    # Nifty Next 50 + BSE Sensex additional
    "ADANIGREEN.NS", "ADANIPOWER.NS", "AMBUJACEM.NS", "AUROPHARMA.NS",
    "BANDHANBNK.NS", "BANKBARODA.NS", "BEL.NS", "BERGEPAINT.NS",
    "BIOCON.NS", "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS",
    "COLPAL.NS", "CONCOR.NS", "DABUR.NS", "DALBHARAT.NS",
    "DLF.NS", "FEDERALBNK.NS", "GAIL.NS", "GODREJCP.NS",
    "GODREJPROP.NS", "HAVELLS.NS", "HINDPETRO.NS", "IDFCFIRSTB.NS",
    "INDIGO.NS", "INDUSTOWER.NS", "IOC.NS", "IRCTC.NS",
    "JUBLFOOD.NS", "LICI.NS", "LUPIN.NS", "MARICO.NS",
    "MCDOWELL-N.NS", "MPHASIS.NS", "MRF.NS", "MUTHOOTFIN.NS",
    "NAUKRI.NS", "NMDC.NS", "OBEROIRLTY.NS", "OFSS.NS",
    "PAGEIND.NS", "PEL.NS", "PERSISTENT.NS", "PETRONET.NS",
    "PFC.NS", "PIDILITIND.NS", "PIIND.NS", "PNB.NS",
    "POLYCAB.NS", "RECLTD.NS", "SBICARD.NS", "SHREECEM.NS",
    "SIEMENS.NS", "SRF.NS", "TATACOMM.NS", "TATAELXSI.NS",
    "TATAPOWER.NS", "TORNTPHARM.NS", "TRENT.NS", "VEDL.NS",
    "VOLTAS.NS", "ZOMATO.NS", "ZYDUSLIFE.NS",
],

"korea_extended": [
    # KOSPI 200 additional (.KS suffix)
    "000150.KS", "000210.KS", "000240.KS", "000670.KS", "000880.KS",
    "001040.KS", "001120.KS", "001230.KS", "001440.KS", "001450.KS",
    "001740.KS", "001800.KS", "002310.KS", "002380.KS", "003410.KS",
    "003550.KS", "003620.KS", "004170.KS", "004370.KS", "004800.KS",
    "004990.KS", "005070.KS", "005180.KS", "005250.KS", "005300.KS",
    "005830.KS", "005850.KS", "005940.KS", "006260.KS", "006360.KS",
    "006800.KS", "007310.KS", "008060.KS", "008770.KS", "009150.KS",
    "009240.KS", "009830.KS", "010060.KS", "010120.KS", "010140.KS",
    "010780.KS", "011170.KS", "011210.KS", "011780.KS", "011790.KS",
    "012450.KS", "012750.KS", "014680.KS", "015760.KS", "016380.KS",
    "017800.KS", "018250.KS", "018880.KS", "019170.KS", "020000.KS",
    "020150.KS", "021240.KS", "023530.KS", "024110.KS", "025540.KS",
    "026960.KS", "028050.KS", "028260.KS", "029780.KS", "030000.KS",
    "030200.KS", "032640.KS", "032830.KS", "033780.KS", "034220.KS",
    "034730.KS", "035250.KS", "035420.KS", "036460.KS", "036570.KS",
    "039130.KS", "042660.KS", "042670.KS", "047040.KS", "047050.KS",
    "047810.KS", "051900.KS", "051910.KS", "053800.KS", "055550.KS",
    "058470.KS", "066570.KS", "068270.KS", "069500.KS", "071050.KS",
    "078930.KS", "086790.KS", "090430.KS", "096770.KS", "097950.KS",
    "105560.KS", "112610.KS", "138930.KS", "161390.KS", "180640.KS",
],

"australia_extended": [
    # ASX 200 additional (.AX suffix)
    "A2M.AX", "AAA.AX", "ABC.AX", "ABP.AX", "AIA.AX", "ALD.AX", "ALQ.AX",
    "ALU.AX", "ALX.AX", "AMP.AX", "ANN.AX", "APA.AX", "APE.AX", "APM.AX",
    "ARB.AX", "AUB.AX", "AWC.AX", "AZJ.AX", "BAP.AX", "BEN.AX",
    "BGA.AX", "BKW.AX", "BLD.AX", "BOQ.AX", "BPT.AX", "BSL.AX",
    "BTH.AX", "CAR.AX", "CCX.AX", "CGF.AX", "CHC.AX", "CHN.AX",
    "CIA.AX", "CIM.AX", "CLW.AX", "CNU.AX", "COH.AX", "CQR.AX",
    "CRN.AX", "CTD.AX", "CWN.AX", "CWY.AX", "DBI.AX", "DMP.AX",
    "DOW.AX", "DTL.AX", "DXC.AX", "EBO.AX", "EHE.AX", "ELD.AX",
    "EML.AX", "EVN.AX", "EVT.AX", "FLT.AX", "FMG.AX", "FPH.AX",
    "GEM.AX", "GMA.AX", "GNC.AX", "GOZ.AX", "GQG.AX", "GUD.AX",
    "GWA.AX", "HLS.AX", "HMC.AX", "HUB.AX", "HVN.AX", "IEL.AX",
    "IGO.AX", "ILU.AX", "IMD.AX", "INA.AX", "INR.AX", "IOZ.AX",
    "IPH.AX", "IPL.AX", "IRE.AX", "JBH.AX", "JHG.AX", "JIN.AX",
    "KAR.AX", "KGN.AX", "KLS.AX", "KMD.AX", "LFS.AX", "LIC.AX",
    "LNK.AX", "LOV.AX", "LTR.AX", "LYC.AX", "MAF.AX", "MFG.AX",
    "MGR.AX", "MIN.AX", "MND.AX", "MP1.AX", "MPL.AX", "MQG.AX",
    "MTS.AX", "MVF.AX", "NAB.AX", "NCK.AX", "NEC.AX", "NEA.AX",
    "NHC.AX", "NHF.AX", "NIC.AX", "NSR.AX", "NUF.AX", "NWH.AX",
    "NWL.AX", "NXT.AX", "OML.AX", "ORA.AX", "ORE.AX", "ORI.AX",
    "OZL.AX", "PBH.AX", "PDL.AX", "PGH.AX", "PME.AX", "PMV.AX",
],

"canada_extended": [
    # TSX Composite additional (.TO suffix)
    "AEM.TO", "AIF.TO", "ALA.TO", "AP-UN.TO", "ARX.TO", "ATA.TO",
    "ATH.TO", "BAM.TO", "BEI-UN.TO", "BIR.TO", "BN.TO", "BTE.TO",
    "BYD-UN.TO", "CAR-UN.TO", "CCA.TO", "CCL-B.TO", "CHP-UN.TO",
    "CIX.TO", "CLS.TO", "CNE.TO", "CPG.TO", "CPX.TO", "CRR-UN.TO",
    "CTC-A.TO", "CUF-UN.TO", "CWB.TO", "D-UN.TO", "DGC.TO", "DIR-UN.TO",
    "DSG.TO", "ECN.TO", "EFN.TO", "EIF.TO", "EMA.TO", "EMP-A.TO",
    "ERF.TO", "ERO.TO", "FAP.TO", "FCR-UN.TO", "FEC.TO", "GEI.TO",
    "GIL.TO", "GRT-UN.TO", "GUD.TO", "H.TO", "HR-UN.TO", "HWX.TO",
    "IFP.TO", "IGM.TO", "IIP-UN.TO", "IMG.TO", "INE.TO", "ITP.TO",
    "KEY.TO", "KIN.TO", "KMP-UN.TO", "KXS.TO", "LB.TO", "LGT-B.TO",
    "LIF.TO", "LNR.TO", "LUN.TO", "MAG.TO", "MDA.TO", "MFI.TO",
    "MG.TO", "MRE.TO", "MTL.TO", "MTY.TO", "NPI.TO", "NTR.TO",
    "NVA.TO", "OGC.TO", "ONEX.TO", "PKI.TO", "PLC.TO", "PMZ-UN.TO",
    "POU.TO", "PPL.TO", "PRL.TO", "PXT.TO", "QBR-B.TO", "RBA.TO",
    "RNW.TO", "RSI.TO", "SES.TO", "SIA.TO", "SJ.TO", "SJR-B.TO",
    "SLF.TO", "SMU-UN.TO", "SOT-UN.TO", "SPB.TO", "SRU-UN.TO", "STN.TO",
    "SVI.TO", "TCN.TO", "TIH.TO", "TOU.TO", "TPX-B.TO", "TRI.TO",
    "TVE.TO", "WCN.TO", "WCP.TO", "WFG.TO", "WN.TO", "WPK.TO",
    "WTE.TO", "X.TO",
],

"europe_extended": [
    # Additional European stocks not in major indices
    # Poland (.WA suffix = Warsaw)
    "PKO.WA", "PEO.WA", "PZU.WA", "KGH.WA", "DNP.WA", "CDR.WA", "ALE.WA",
    "PKN.WA", "LPP.WA", "SPL.WA", "CCC.WA", "JSW.WA", "MBK.WA", "PGE.WA",
    "OPL.WA",
    # Greece (.AT suffix = Athens)
    "OPAP.AT", "MYTIL.AT", "EUROB.AT", "ETE.AT", "HTO.AT", "ADMIE.AT",
    "ALPHA.AT", "LAMDA.AT", "TENERGY.AT", "QUEST.AT",
    # Turkey (.IS suffix = Istanbul)
    "THYAO.IS", "KCHOL.IS", "GARAN.IS", "ASELS.IS", "EREGL.IS", "BIMAS.IS",
    "SAHOL.IS", "SISE.IS", "AKBNK.IS", "TUPRS.IS", "TCELL.IS", "PETKM.IS",
    "TOASO.IS", "FROTO.IS", "ARCLK.IS",
    # Czech Republic (.PR suffix = Prague)
    "CEZ.PR", "KOMB.PR", "MONET.PR", "BAACEZ.PR", "VIG.PR",
    # Hungary (.BD suffix = Budapest)
    "OTP.BD", "MOL.BD", "MTEL.BD", "RICHTER.BD",
    # Romania (.BVB = Bucharest)
    "TLV.BVB", "SNP.BVB", "H2O.BVB", "BRD.BVB", "FP.BVB",
],

"global_adrs": [
    # Major ADRs trading on US exchanges (no suffix needed)
    # European ADRs
    "ASML", "NVO", "AZN", "SHEL", "BP", "GSK", "UL", "DEO", "BHP", "RIO",
    "SAP", "TM", "HMC", "SONY", "MUFG", "SMFG", "NMR", "KB", "SHG", "WBK",
    "DB", "UBS", "CS", "ING", "BBVA", "SAN", "BCS", "LYG", "NWG", "HSBC",
    "VOD", "ERIC", "NOK", "PHG", "NXPI", "STM", "RACE", "STLA", "VWAGY",
    "BMWYY", "NSRGY", "LVMUY", "PPRUY", "HESAY", "CFRUY", "LRLCY",
    # Japanese ADRs
    "TM", "HMC", "SONY", "MUFG", "SMFG", "NMR", "NTDOY", "KYOCY", "FANUY",
    "TCOM", "DKILY", "SFTBY", "MFG", "IX",
    # Korean ADRs
    "KB", "SHG", "WF", "LPL", "PKX",
    # Latin American ADRs
    "PBR", "VALE", "ITUB", "BBD", "ABEV", "SBS", "AMX", "FMX", "KOF",
    "BSAC", "SQM", "EC", "GGAL", "YPF", "BMA", "PAM", "GLOB",
    # African ADRs
    "GOLD", "AU", "HMY", "DRD", "SBSW", "SSL",
    # Indian ADRs
    "INFY", "WIT", "HDB", "IBN", "RDY", "TTM",
    # Chinese ADRs (additional to china package)
    "TCOM", "BGNE", "ZH", "LEGN", "CAN", "WB", "DADA", "BEKE", "ATHM",
    "HUYA", "DOYU", "GRVY", "LU", "XNET", "YY", "API", "LITB", "NIU",
],

"us_spacs_desspacs": [
    # De-SPACs and notable SPACs that have completed mergers
    "DKNG", "LCID", "RIVN", "JOBY", "LILM", "RKLB", "SPCE", "DNA",
    "MVST", "ORGN", "SOFI", "CLOV", "OPEN", "UWMC", "BARK",
    "VIEW", "PAYO", "STEM", "GENI", "MKTW", "OPAD", "ASTS", "ALIT",
    "HLAH", "CNVY", "QSI", "SNAX", "AVAN", "MAPS", "DCGO", "SMRT",
],

"us_Russell_1000_add": [
    # Russell 1000 stocks not already in S&P 500 / NASDAQ 100
    "ABNB", "AI", "ALNY", "ANSS", "APP", "AXON", "AZO", "BILL", "BJ",
    "BLDR", "BMRN", "BSY", "CELH", "CFLT", "CHDN", "CIEN", "CPNG",
    "CSGP", "CYBR", "DASH", "DKNG", "DOCU", "DOX", "DUOL", "DXCM",
    "ESTC", "FIVE", "FROG", "FRSH", "GFS", "GLOB", "GLPI", "GNTX",
    "GTLB", "HALO", "IIPR", "INSP", "IOT", "KVYO", "LPLA", "LSCC",
    "MANH", "MASI", "MDB", "MEDP", "MGNI", "MNDY", "MPWR", "MSTR",
    "NET", "NVAX", "NVST", "OLED", "PAYC", "PCTY", "PCOR", "PLNT",
    "QLYS", "RBC", "RGEN", "RIVN", "ROKU", "RUN", "SAIA", "SAMSARA",
    "SHOP", "SN", "SOUN", "STAG", "TDG", "TENB", "TOST", "TREX",
    "TW", "U", "VEEV", "VRRM", "WDAY", "WIX", "WSC", "WSO", "YETI",
    "ZI", "ZM", "ZS",
],

"us_russell2000_broad": [
    # Broad Russell 2000 coverage - additional small caps (~500 symbols)
    "AAOI", "AAWW", "ABG", "ABMD", "ACAD", "ACES", "ACHC", "ACLS", "ACNB",
    "ADNT", "AEHR", "AEIS", "AEL", "AERI", "AES", "AFG", "AGCO", "AGEN",
    "AGYS", "AHCO", "AHH", "AIN", "AIRC", "AJRD", "AKR", "ALEC", "ALEX",
    "ALGM", "ALHC", "ALIT", "ALKS", "ALLE", "ALLO", "ALRM", "ALSN", "ALT",
    "ALTO", "AMAL", "AMBA", "AMBC", "AMC", "AMEH", "AMG", "AMK", "AMKR",
    "AMN", "AMPH", "AMPL", "AMRC", "AMSF", "AMSWA", "AMWD", "ANAB", "ANDE",
    "ANGO", "ANIK", "ANIP", "ANSS", "AORT", "APAM", "APEI", "APGE", "APLE",
    "APLS", "APOG", "APPF", "APPN", "APPS", "AQST", "ARAV", "ARCB", "ARCE",
    "ARCT", "ARDX", "ARIS", "ARKO", "ARLO", "ARMK", "ARNC", "AROC", "ARRY",
    "ARVN", "ASAN", "ASND", "ASTE", "ASUR", "ATEC", "ATEN", "ATER", "ATEX",
    "ATGE", "ATKR", "ATNI", "ATRA", "ATRC", "ATSG", "AVAV", "AVAL", "AVDL",
    "AVDX", "AVES", "AVID", "AVNS", "AVPT", "AVTA", "AVXL", "AXGN", "AXL",
    "AXNX", "AY", "AYI", "AZEK", "AZPN", "AZZ", "BALY", "BAND", "BANF",
    "BANR", "BBCP", "BBDC", "BBIO", "BBSI", "BCBP", "BCO", "BCOV", "BCPC",
    "BDTX", "BFS", "BGS", "BHE", "BHVN", "BKD", "BKE", "BKH", "BKU",
    "BLBD", "BLFS", "BLKB", "BLMN", "BLUE", "BMBL", "BNL", "BOISE", "BOOT",
    "BOX", "BPMC", "BPOP", "BRC", "BRCC", "BRG", "BRKL", "BRKR", "BRX",
    "BSIG", "BTG", "BTDR", "BTU", "BUR", "BVH", "BVS", "BYRN", "CAKE",
    "CALM", "CALX", "CAMP", "CARG", "CARS", "CASA", "CATO", "CATY", "CBAN",
    "CBRL", "CBU", "CCS", "CCSI", "CDLX", "CDMO", "CECO", "CENX", "CERS",
    "CFFN", "CGNX", "CHCO", "CHCT", "CHGG", "CHRD", "CHRS", "CIVB", "CLBK",
    "CLDT", "CLDX", "CLFD", "CLNE", "CLPT", "CLSK", "CLVS", "CLVT", "CMBM",
    "CMCO", "CMD", "CMLS", "CMPR", "CMRE", "CMP", "CNDT", "CNOB", "CNSL",
    "COGT", "COHU", "COKE", "COLL", "COMP", "CONN", "COOP", "CORZ", "CORT",
    "COUR", "COWN", "CPBI", "CPF", "CPK", "CPRX", "CRBG", "CRDO", "CRGY",
    "CRK", "CRMD", "CRNC", "CROX", "CRS", "CRVL", "CRVS", "CSQ", "CSTL",
    "CSTM", "CSWI", "CTBI", "CTO", "CTS", "CUBI", "CURV", "CVBF", "CVCO",
    "CVGI", "CVLT", "CWEN", "CWH", "CWST", "CWT", "CXM", "CYBR", "CYTK",
    "CZFS", "DAIO", "DAR", "DAVA", "DBD", "DBRG", "DCI", "DCGO", "DDD",
    "DDS", "DERM", "DFH", "DGII", "DIOD", "DJT", "DLHC", "DLX", "DMRC",
    "DNOW", "DNUT", "DOMO", "DOOR", "DORM", "DOX", "DRVN", "DSGX", "DVAX",
    "DV", "DY", "DXPE", "EARN", "EBON", "ECPG", "EFSC", "EIG", "ELAN",
    "ELBM", "ELF", "ELTK", "ELVN", "EME", "ENTA", "EPC", "EPRT", "ERAS",
    "ERII", "ESGR", "ESTE", "ETRN", "EVBG", "EVER", "EWTX", "EXAI", "EXLS",
    "EXPI", "EXPO", "EYE", "FARO", "FATE", "FCEL", "FDP", "FIVN", "FIZZ",
    "FLGT", "FLIC", "FLNC", "FLWS", "FN", "FOLD", "FORM", "FOXF", "FREY",
    "FRGE", "FRPT", "FRSH", "FTCI", "FTRE", "FULC", "FULT", "FUV", "GABC",
    "GBCI", "GBTG", "GCT", "GDRX", "GEOS", "GFF", "GH", "GIII", "GLBE",
    "GLNG", "GMS", "GO", "GOGL", "GOSS", "GRND", "GSHD", "GTLB", "GTLS",
    "GYRE", "HALO", "HAYW", "HEES", "HIMS", "HL", "HLLY", "HLX", "HMST",
    "HNI", "HOLI", "HOOD", "HUBG", "HUN", "HUT", "HZNP", "IAC", "IBRX",
    "ICFI", "ICHR", "IDYA", "IESC", "IIPR", "IMNM", "IMVT", "INBX", "INFN",
    "INMD", "INNV", "INSP", "INTA", "IOSP", "IONQ", "IRTC", "ISEE", "IVA",
    "JBT", "JJSF", "JOBY", "JUST", "KALU", "KAR", "KLIC", "KNSA", "KOD",
    "KREF", "KROS", "KTB", "KTOS", "KVYO", "LBRT", "LCID", "LFST", "LGIH",
    "LILM", "LIVN", "LKFN", "LMND", "LNSR", "LOAR", "LOVE", "LQDA", "LRMR",
    "LZ", "MARA", "MATW", "MAX", "MCFT", "MCY", "ME", "MGEE", "MGY",
    "MIRM", "MIR", "MITK", "MLKN", "MNDY", "MRCY", "MRSN", "MSGE", "MSGS",
    "MTX", "MWA", "MYGN", "NABL", "NARI", "NBTB", "NCNO", "NKTR", "NMRK",
],

"us_otc_notable": [
    # Notable OTC / Pink Sheets (higher risk, international companies)
    "TCEHY", "BABA", "NSRGY", "RHHBY", "LVMUY", "PPRUY", "HESAY", "CFRUY",
    "LRLCY", "IDEXY", "DSNKY", "DANOY", "HENKY", "UNICY", "NNGPF", "INGVF",
    "ADDYY", "POAHY", "VWAGY", "BMWYY", "DAIMF", "VLVLY", "ABLZF", "BNTGY",
    "SMAWF", "ATLCY", "KYOCY", "FANUY", "NTDOY", "SFTBY", "DKILY", "FUJHY",
    "TKOMY", "TOELY", "MZDAY", "AHCHY", "SMPNY", "BRKNY", "DNZOY", "HOKCY",
    "RCRRF", "SHECY", "CMPNY", "HENOY", "SSUMY", "MNPLY", "DASTY", "ESLOY",
    "PCRFY", "BYDDY", "CTTAY", "HKXCY", "CLPBY", "BABAF", "ALIZY", "ITOCY",
    "MARUY", "SUMCY", "MITSF", "CJPRY", "KDDIY", "NPPXF", "NIPNF", "RNECY",
],

}


# ══════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════

# Default packages activated for new users (reasonable scan time)
DEFAULT_ACTIVE_PACKAGES = [
    "us_mega_cap",
    "sector_semiconductors",
    "sector_tech_software",
    "sector_biotech",
    "sector_fintech",
    "sector_clean_energy",
    "theme_ai",
]


def get_package_symbols(packages: List[str]) -> List[str]:
    """Get deduplicated symbols for the given package names."""
    seen = set()
    result = []
    for pkg in packages:
        for sym in WATCHLIST_PACKAGES.get(pkg, []):
            if sym not in seen:
                seen.add(sym)
                result.append(sym)
    return result


def get_all_symbols() -> List[str]:
    """Get all unique symbols across all packages."""
    return get_package_symbols(list(WATCHLIST_PACKAGES.keys()))


def list_packages() -> List[Tuple[str, str, int, str]]:
    """Return list of (key, name, symbol_count, region) for all packages."""
    result = []
    for key, symbols in WATCHLIST_PACKAGES.items():
        meta = PACKAGE_META.get(key, {})
        result.append((
            key,
            meta.get("name", key),
            len(symbols),
            meta.get("region", "?"),
        ))
    return result


def list_packages_by_region() -> Dict[str, List[Tuple[str, str, int]]]:
    """Return packages grouped by region."""
    by_region: Dict[str, List[Tuple[str, str, int]]] = {}
    for key, symbols in WATCHLIST_PACKAGES.items():
        meta = PACKAGE_META.get(key, {})
        region = meta.get("region", "Other")
        if region not in by_region:
            by_region[region] = []
        by_region[region].append((key, meta.get("name", key), len(symbols)))
    return by_region


def get_total_symbol_count() -> int:
    """Total unique symbols across all packages."""
    return len(get_all_symbols())
