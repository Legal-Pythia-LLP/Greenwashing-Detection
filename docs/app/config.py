# 配置与常量

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'de': 'German',
    'it': 'Italian'
}

GREENWASHING_KEYWORDS = {
    'en': [
        'sustainable', 'green', 'eco-friendly', 'carbon neutral', 'clean energy',
        'renewable', 'environmentally responsible', 'climate-friendly', 'net-zero',
        'carbon footprint', 'biodegradable', 'organic', 'natural', 'zero waste',
        'climate action', 'sustainable development', 'environmental stewardship'
    ],
    'de': [
        'nachhaltig', 'grün', 'umweltfreundlich', 'klimaneutral', 'saubere energie',
        'erneuerbar', 'umweltverantwortlich', 'klimafreundlich', 'netto-null',
        'co2-fußabdruck', 'biologisch abbaubar', 'organisch', 'natürlich', 'null abfall',
        'klimaschutz', 'nachhaltige entwicklung', 'umweltschutz'
    ],
    'it': [
        'sostenibile', 'verde', 'eco-compatibile', 'carbon neutral', 'energia pulita',
        'rinnovabile', 'responsabile ambientale', 'climate-friendly', 'zero netto',
        'impronta carbonica', 'biodegradabile', 'organico', 'naturale', 'zero rifiuti',
        'azione climatica', 'sviluppo sostenibile', 'gestione ambientale'
    ]
}

ANALYSIS_PROMPTS = {
    'en': {
        'company_extraction': "Extract the company name from this context. Return only the company name, nothing else.",
        'greenwashing_analysis': """Analyze the following ESG document content for greenwashing indicators:\n\nContent: {content}\n\nLook for:\n1. Vague or unsubstantiated claims\n2. Lack of specific metrics or targets\n3. Misleading terminology\n4. Cherry-picked data\n5. Absence of third-party verification\n\nProvide specific evidence and scoring rationale.""",
        'metrics_calculation': """Based on the following ESG analysis, calculate specific greenwashing metrics:\n\nAnalysis: {analysis}\n\nCalculate scores (0-100) for each metric:\n1. Vague Language Score\n2. Evidence Quality Score\n3. Transparency Score\n4. Measurability Score\n5. Third-party Verification Score\n\nFormat as JSON with detailed evidence for each metric."""
    },
    'de': {
        'company_extraction': "Extrahieren Sie den Firmennamen aus diesem Kontext. Geben Sie nur den Firmennamen zurück, nichts anderes.",
        'greenwashing_analysis': """Analysieren Sie den folgenden ESG-Dokumentinhalt auf Greenwashing-Indikatoren:\n\nInhalt: {content}\n\nSuchen Sie nach:\n1. Vagen oder unbegründeten Behauptungen\n2. Fehlenden spezifischen Kennzahlen oder Zielen\n3. Irreführender Terminologie\n4. Selektiv ausgewählten Daten\n5. Fehlender Drittpartei-Verifizierung\n\nGeben Sie spezifische Belege und Bewertungslogik an.""",
        'metrics_calculation': """Basierend auf der folgenden ESG-Analyse berechnen Sie spezifische Greenwashing-Kennzahlen:\n\nAnalyse: {analysis}\n\nBerechnen Sie Scores (0-100) für jede Kennzahl:\n1. Score für vage Sprache\n2. Score für Beweisqualität\n3. Transparenz-Score\n4. Messbarkeits-Score\n5. Drittpartei-Verifizierungs-Score\n\nFormatieren Sie als JSON mit detaillierten Belegen für jede Kennzahl."""
    },
    'it': {
        'company_extraction': "Estrai il nome dell'azienda da questo contesto. Restituisci solo il nome dell'azienda, nient'altro.",
        'greenwashing_analysis': """Analizza il seguente contenuto del documento ESG per indicatori di greenwashing:\n\nContenuto: {content}\n\nCerca:\n1. Affermazioni vaghe o non supportate\n2. Mancanza di metriche o obiettivi specifici\n3. Terminologia fuorviante\n4. Dati selezionati ad hoc\n5. Assenza di verifica da parte terza\n\nFornisci evidenze specifiche e razionale di valutazione.""",
        'metrics_calculation': """Basato sulla seguente analisi ESG, calcola metriche specifiche di greenwashing:\n\nAnalisi: {analysis}\n\nCalcola punteggi (0-100) per ogni metrica:\n1. Punteggio Linguaggio Vago\n2. Punteggio Qualità delle Prove\n3. Punteggio Trasparenza\n4. Punteggio Misurabilità\n5. Punteggio Verifica Terze Parti\n\nFormatta come JSON con evidenze dettagliate per ogni metrica."""
    }
} 