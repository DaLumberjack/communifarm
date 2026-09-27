/**
 * Simpler Wood Lover recipe + mock NFC UIDs (matches mock_esp32dev_scale.yaml).
 * Amounts match custom_components/communifarm/domain/recipe.py.
 */
export type WoodLoverLine = {
  label: string;
  nfcUid: string;
  /** Amount placed on the scale for this line (grams for g; nominal grams for qts stubs). */
  amountG: number;
  unit: "g" | "qts";
};

export const WOOD_LOVER_WEIGH_STEPS: WoodLoverLine[] = [
  { label: "hardwood pellets", nfcUid: "nfc-hardwood-pellets", amountG: 3000, unit: "g" },
  { label: "hardwood shavings", nfcUid: "nfc-hardwood-shavings", amountG: 200, unit: "g" },
  {
    label: "shredded organic wheat straw",
    nfcUid: "nfc-wheat-straw",
    amountG: 500,
    unit: "g",
  },
  {
    label: "organic worm castings",
    nfcUid: "nfc-worm-castings",
    amountG: 250,
    unit: "g",
  },
  { label: "organic wheat bran", nfcUid: "nfc-wheat-bran", amountG: 200, unit: "g" },
  // Volumetric recipe lines: mock still records grams; use a small positive mass.
  { label: "vermiculite", nfcUid: "nfc-vermiculite", amountG: 2, unit: "qts" },
  { label: "coco coir", nfcUid: "nfc-coco-coir", amountG: 2, unit: "qts" },
  { label: "gypsum", nfcUid: "nfc-gypsum", amountG: 200, unit: "g" },
  { label: "potash", nfcUid: "nfc-potash", amountG: 50, unit: "g" },
];

/** Empty mix-bin mass before each tare (simulates container on the scale). */
export const MIX_BIN_TARE_G = 1000;
