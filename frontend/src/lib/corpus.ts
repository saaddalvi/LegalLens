// The Acts in the Corpus, by name (mirrors the backend's ingestion).
export const CORPUS_ACTS = [
  "Constitution of India",
  "Bharatiya Nyaya Sanhita",
  "Bharatiya Nagarik Suraksha Sanhita",
  "Bharatiya Sakshya Adhiniyam",
  "Indian Penal Code",
  "Code of Criminal Procedure",
  "Indian Evidence Act",
  "Consumer Protection Act",
  "Transfer of Property Act",
  "Model Tenancy Act",
  "Code on Wages",
  "Industrial Relations Code",
  "Code on Social Security",
  "Occupational Safety, Health and Working Conditions Code",
] as const;

export const REPEAL_NOTE =
  "The Indian Penal Code, Code of Criminal Procedure and Indian Evidence Act are repealed. Their Provisions point to the replacements in the Bharatiya Nyaya Sanhita (BNS), Bharatiya Nagarik Suraksha Sanhita (BNSS) and Bharatiya Sakshya Adhiniyam (BSA), so you can still ask about an old section number.";

export const EXAMPLE_QUERIES = {
  en: [
    "What rights do I have if I am arrested?",
    "What is the punishment for murder?",
    "I bought a defective product. Where can I file a consumer complaint?",
    "What is IPC 302?",
  ],
  hi: [
    "अगर मुझे गिरफ्तार किया जाए तो मेरे क्या अधिकार हैं?",
    "हत्या की सज़ा क्या है?",
    "मेरी कंपनी समय पर वेतन नहीं दे रही है, कानून क्या कहता है?",
  ],
};
