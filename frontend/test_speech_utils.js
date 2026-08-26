import {
  detectResponseLanguage,
  findTeluguVoice,
  findEnglishVoice,
  selectVoiceForText,
} from "./src/utils/speechUtils.js";

let passed = 0;
let failed = 0;

function check(title, condition, details = "") {
  if (condition) {
    passed++;
    console.log(`  [PASS] ${title} ${details ? `(${details})` : ""}`);
  } else {
    failed++;
    console.log(`  [FAIL] ${title} ${details ? `(${details})` : ""}`);
  }
}

console.log("\n=== TEST: Response Language Detection ===");
check(
  "1. Pure Telugu sentence",
  detectResponseLanguage("మీరు డాక్టర్ రాజేష్ని చివరిసారి ఆగస్టు 24న కలిశారు.") === "te"
);
check(
  "2. Mixed Telugu + English entities",
  detectResponseLanguage("Dr. Rajesh తో next follow-up August 29న ఉంది.") === "te"
);
check(
  "3. Pure English sentence",
  detectResponseLanguage("You last met Dr. Rajesh on August 24.") === "en"
);
check(
  "4. English with medical terms",
  detectResponseLanguage("Discussed CardioPress-50 and scheduled follow-up with Dr. Sharma at Apollo Hospital.") === "en"
);
check(
  "5. Empty/null input",
  detectResponseLanguage("") === "en" && detectResponseLanguage(null) === "en"
);

console.log("\n=== TEST: Telugu Voice Discovery ===");
const sampleVoices = [
  { name: "Microsoft David", lang: "en-US" },
  { name: "Microsoft Zira", lang: "en-US" },
  { name: "Google US English", lang: "en-US" },
  { name: "Google Indian English", lang: "en-IN" },
  { name: "Microsoft Mohan - Telugu (India)", lang: "te-IN" },
  { name: "Google తెలుగు", lang: "te-IN" },
];

const voicesNoTelugu = [
  { name: "Microsoft David", lang: "en-US" },
  { name: "Microsoft Zira", lang: "en-US" },
  { name: "Google Indian English", lang: "en-IN" },
];

const teVoice1 = findTeluguVoice(sampleVoices);
check("6. Finds te-IN voice when available", teVoice1 !== null && teVoice1.lang === "te-IN", teVoice1?.name);

const teVoiceNone = findTeluguVoice(voicesNoTelugu);
check("7. Returns null when no Telugu voice exists in browser", teVoiceNone === null);

console.log("\n=== TEST: English Voice Discovery ===");
const enVoiceIndia = findEnglishVoice(sampleVoices);
check("8. Prefers Indian English (en-IN) for CRM context", enVoiceIndia !== null && enVoiceIndia.lang === "en-IN", enVoiceIndia?.name);

const enVoiceUS = findEnglishVoice([
  { name: "Microsoft David", lang: "en-US" },
  { name: "Microsoft Zira", lang: "en-US" },
]);
check("9. Falls back to en-US when en-IN is absent", enVoiceUS !== null && enVoiceUS.lang === "en-US", enVoiceUS?.name);

console.log("\n=== TEST: Strict Voice Selection (NO English Fallback for Telugu) ===");
const teluguText = "మీరు డాక్టర్ రాజేష్ని చివరిసారి ఆగస్టు 24న కలిశారు.";

// Case A: Telugu text + Telugu voice available
const selectionWithTe = selectVoiceForText(teluguText, sampleVoices);
check("10. Telugu text with Te voice -> assigns Te voice", selectionWithTe.voice !== null && selectionWithTe.isSupported === true);
check("11. Language code set to te-IN", selectionWithTe.lang === "te-IN");

// Case B: Telugu text + NO Telugu voice available (CRITICAL)
const selectionWithoutTe = selectVoiceForText(teluguText, voicesNoTelugu);
check(
  "12. CRITICAL: Telugu text with NO Te voice -> voice MUST BE NULL (no English fallback)",
  selectionWithoutTe.voice === null && selectionWithoutTe.isSupported === false
);
check("13. Detected language remains 'te'", selectionWithoutTe.detectedLanguage === "te");

// Case C: English text
const englishText = "You last met Dr. Rajesh on August 24.";
const selectionEn = selectVoiceForText(englishText, sampleVoices);
check("14. English text selects English voice", selectionEn.voice !== null && selectionEn.detectedLanguage === "en");

// Case D: Mixed text
const mixedText = "Dr. Rajesh తో next follow-up August 29న ఉంది.";
const selectionMixedWithTe = selectVoiceForText(mixedText, sampleVoices);
check("15. Mixed text selects Telugu voice when available", selectionMixedWithTe.voice !== null && selectionMixedWithTe.detectedLanguage === "te");

const selectionMixedWithoutTe = selectVoiceForText(mixedText, voicesNoTelugu);
check("16. Mixed text without Telugu voice -> voice is null (no English mangling)", selectionMixedWithoutTe.voice === null);

console.log("\n" + "=".repeat(50));
console.log(`Speech Utils Test Summary: ${passed} passed, ${failed} failed`);
if (failed === 0) {
  console.log("ALL TESTS PASSED!\n");
  process.exit(0);
} else {
  console.log("SOME TESTS FAILED!\n");
  process.exit(1);
}
