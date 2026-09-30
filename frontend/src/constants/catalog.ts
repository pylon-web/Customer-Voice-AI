/**
 * Capital One product catalog and platform metadata constants.
 * Fallbacks and display helpers with authentic Capital One product tiers and card styling.
 */

export interface ProductMeta {
  id: string;
  name: string;
  family: string;
  tier: string;
  color: string;
  cardStyle: string;
  description: string;
}

export const CAPITAL_ONE_CATALOG: ProductMeta[] = [
  // Credit Cards
  {
    id: 'venture_x',
    name: 'Venture X Rewards',
    family: 'Credit Cards',
    tier: 'Premium Travel Rewards',
    color: 'border-blue-400 text-sky-300 bg-blue-950/60',
    cardStyle: 'bg-gradient-to-r from-[#07192F] via-[#0B2545] to-[#0F3563] border-[#1E4D80] text-sky-200',
    description: 'Premium travel rewards card with airport lounge access and 10x travel miles.',
  },
  {
    id: 'venture',
    name: 'Venture Rewards',
    family: 'Credit Cards',
    tier: 'Travel Miles & Partner Transfers',
    color: 'border-blue-500 text-blue-300 bg-blue-950/50',
    cardStyle: 'bg-gradient-to-r from-[#081C33] to-[#0D325E] border-[#1B4B82] text-blue-200',
    description: 'Unlimited 2x miles travel card with transfer partner flexibility.',
  },
  {
    id: 'savor_one',
    name: 'SavorOne Cash Rewards',
    family: 'Credit Cards',
    tier: 'Dining & Entertainment 3%',
    color: 'border-amber-600 text-amber-300 bg-amber-950/50',
    cardStyle: 'bg-gradient-to-r from-[#201007] via-[#381B0D] to-[#542713] border-[#8C461F] text-amber-200',
    description: 'Dining, entertainment, and grocery cash back card with no annual fee.',
  },
  {
    id: 'quicksilver',
    name: 'Quicksilver Cash Rewards',
    family: 'Credit Cards',
    tier: 'Unlimited 1.5% Cash Back',
    color: 'border-slate-400 text-slate-200 bg-slate-800/60',
    cardStyle: 'bg-gradient-to-r from-[#17202A] via-[#243342] to-[#2E4154] border-[#566D85] text-slate-100',
    description: 'Flat 1.5% cash back on all purchases card.',
  },
  {
    id: 'platinum',
    name: 'Capital One Platinum',
    family: 'Credit Cards',
    tier: 'Credit Building & Reconstruction',
    color: 'border-slate-500 text-slate-300 bg-slate-900/60',
    cardStyle: 'bg-gradient-to-r from-[#151D28] to-[#263546] border-[#44576D] text-slate-200',
    description: 'Credit building and credit reconstruction card with automatic reviews.',
  },
  {
    id: 'spark_cash_plus',
    name: 'Spark Cash Plus',
    family: 'Credit Cards',
    tier: 'Small Business 2% Cash Back',
    color: 'border-emerald-500 text-emerald-300 bg-emerald-950/50',
    cardStyle: 'bg-gradient-to-r from-[#062016] via-[#0B3828] to-[#12543C] border-[#1D7756] text-emerald-200',
    description: 'Small business charge card with unlimited 2% cash back.',
  },

  // Consumer Banking (360)
  {
    id: 'banking_360_checking',
    name: '360 Checking',
    family: 'Consumer Banking',
    tier: 'Fee-Free Everyday Checking',
    color: 'border-teal-500 text-teal-300 bg-teal-950/50',
    cardStyle: 'bg-gradient-to-r from-[#041D24] to-[#0A3D4C] border-[#136A84] text-teal-200',
    description: 'Fee-free checking account with debit card and early paycheck deposit.',
  },
  {
    id: 'banking_360_savings',
    name: '360 Performance Savings',
    family: 'Consumer Banking',
    tier: 'High-Yield Online Savings',
    color: 'border-emerald-400 text-emerald-300 bg-emerald-950/50',
    cardStyle: 'bg-gradient-to-r from-[#052119] to-[#0D4434] border-[#16785D] text-emerald-200',
    description: 'High-yield online savings account with fee-free transfers.',
  },
  {
    id: 'banking_360_cd',
    name: '360 Certificate of Deposit',
    family: 'Consumer Banking',
    tier: 'Fixed-Term Guaranteed Yield',
    color: 'border-teal-600 text-teal-300 bg-teal-950/40',
    cardStyle: 'bg-gradient-to-r from-[#041E26] to-[#093C4C] border-[#12657F] text-teal-200',
    description: 'Fixed-term deposit accounts with competitive guaranteed yield.',
  },
  {
    id: 'banking_360_kids',
    name: 'MONEY Teen Checking',
    family: 'Consumer Banking',
    tier: 'Joint Teen & Parental Controls',
    color: 'border-indigo-400 text-indigo-300 bg-indigo-950/40',
    cardStyle: 'bg-gradient-to-r from-[#0E1530] to-[#192657] border-[#2A3F90] text-indigo-200',
    description: 'Joint teen checking account with parental controls and debit card.',
  },

  // Auto Finance
  {
    id: 'auto_navigator',
    name: 'Auto Navigator',
    family: 'Auto Finance',
    tier: 'Direct Pre-qualification',
    color: 'border-orange-500 text-orange-300 bg-orange-950/50',
    cardStyle: 'bg-gradient-to-r from-[#240F08] via-[#3E1A0E] to-[#592615] border-[#8F3E22] text-orange-200',
    description: 'Direct-to-consumer auto pre-qualification and dealer inventory financing.',
  },
  {
    id: 'auto_refinance',
    name: 'Auto Refinance',
    family: 'Auto Finance',
    tier: 'Rate Reduction Refinancing',
    color: 'border-orange-600 text-orange-300 bg-orange-950/40',
    cardStyle: 'bg-gradient-to-r from-[#220D07] to-[#4A1C0F] border-[#7F321B] text-orange-200',
    description: 'Vehicle loan refinancing platform with lower rate pre-qualification.',
  },

  // Digital & AI Platforms
  {
    id: 'c1_mobile_ios',
    name: 'Capital One Mobile (iOS)',
    family: 'Digital & AI',
    tier: 'Flagship iOS Banking App',
    color: 'border-sky-500 text-sky-300 bg-sky-950/50',
    cardStyle: 'bg-gradient-to-r from-[#061B30] to-[#0C355E] border-[#1B579B] text-sky-200',
    description: 'Flagship iOS mobile banking app with Face ID and digital wallet support.',
  },
  {
    id: 'c1_mobile_android',
    name: 'Capital One Mobile (Android)',
    family: 'Digital & AI',
    tier: 'Android Banking Experience',
    color: 'border-green-500 text-green-300 bg-green-950/50',
    cardStyle: 'bg-gradient-to-r from-[#072115] to-[#0E422B] border-[#18754D] text-green-200',
    description: 'Android banking application supporting fingerprint authentication.',
  },
  {
    id: 'eno_virtual_assistant',
    name: 'Eno Virtual Assistant',
    family: 'Digital & AI',
    tier: 'AI Assistant & Virtual Cards',
    color: 'border-purple-500 text-purple-300 bg-purple-950/50',
    cardStyle: 'bg-gradient-to-r from-[#170E28] via-[#2A184A] to-[#3D236B] border-[#6539B3] text-purple-200',
    description: 'AI-driven natural language virtual assistant and virtual card generator.',
  },
  {
    id: 'creditwise',
    name: 'CreditWise',
    family: 'Digital & AI',
    tier: 'Free Credit Monitoring & VantageScore',
    color: 'border-indigo-500 text-indigo-300 bg-indigo-950/50',
    cardStyle: 'bg-gradient-to-r from-[#0F142D] to-[#1C2654] border-[#30418E] text-indigo-200',
    description: 'Free TransUnion VantageScore credit score simulator and dark web monitor.',
  },
  {
    id: 'c1_shopping_extension',
    name: 'Capital One Shopping',
    family: 'Digital & AI',
    tier: 'Coupons & Cashback Extension',
    color: 'border-rose-500 text-rose-300 bg-rose-950/50',
    cardStyle: 'bg-gradient-to-r from-[#260C14] to-[#4E182A] border-[#852A47] text-rose-200',
    description: 'Automated coupon finder and cash-back rewards browser extension.',
  },

  // Physical Experiences & Cafes
  {
    id: 'c1_cafe',
    name: 'Capital One Café',
    family: 'Physical & Cafés',
    tier: 'Community Hub & Peet\'s Coffee',
    color: 'border-amber-600 text-amber-300 bg-amber-950/50',
    cardStyle: 'bg-gradient-to-r from-[#261507] via-[#42240D] to-[#5E3413] border-[#9E5720] text-amber-200',
    description: 'Hybrid community workspace, 50% handcrafted beverages, and ambassadors.',
  },
  {
    id: 'c1_branch_network',
    name: 'Capital One Branch',
    family: 'Physical & Cafés',
    tier: 'Full-Service Retail Banking',
    color: 'border-slate-400 text-slate-200 bg-slate-800/60',
    cardStyle: 'bg-gradient-to-r from-[#171E28] to-[#2B384A] border-[#4E6585] text-slate-100',
    description: 'Full-service retail banking branch and ATM network.',
  },
];

export const SOURCE_LABELS: Record<string, { name: string; icon: string }> = {
  apple_app_store: { name: 'Apple App Store', icon: '🍎' },
  google_play_store: { name: 'Google Play Store', icon: '🤖' },
  google_places: { name: 'Google Maps / Places', icon: '📍' },
  chrome_web_store: { name: 'Chrome Web Store', icon: '🌐' },
  trustpilot: { name: 'Trustpilot', icon: '⭐' },
  generic_public: { name: 'Public Feed', icon: '📡' },
};

export const ENTERPRISE_TEAMS = [
  { id: 'digital_eng_mobile', name: 'Digital Engineering - Mobile App', dept: 'Digital Tech' },
  { id: 'payments_ops', name: 'Payments & Fraud Operations', dept: 'Core Operations' },
  { id: 'travel_lounges_prod', name: 'Lounge & Travel Products Operations', dept: 'Premium Card Products' },
  { id: 'cafe_ops', name: 'Café & Branch Experience Operations', dept: 'Retail & Experience' },
  { id: 'digital_ai_security', name: 'Digital & AI Products (Eno / Security)', dept: 'AI & Data Platforms' },
  { id: 'shopping_eng', name: 'Shopping & Browser Extension Engineering', dept: 'Consumer Commerce' },
  { id: 'customer_exp', name: 'Customer Experience & Call Center Operations', dept: 'Brand Experience' },
];

export function getProductMeta(productId?: string): ProductMeta {
  const found = CAPITAL_ONE_CATALOG.find((p) => p.id === productId);
  if (found) return found;
  return {
    id: productId || 'unknown',
    name: productId ? productId.replace(/_/g, ' ') : 'General Product',
    family: 'General',
    tier: 'Financial Product',
    color: 'border-slate-500 text-slate-300 bg-slate-900/40',
    cardStyle: 'bg-slate-900 border-slate-700 text-slate-200',
    description: '',
  };
}
