/**
 * Capital One Enterprise Business Teams and Department Remediation Playbooks.
 */

export interface TeamMeta {
  id: string;
  canonicalId: string;
  name: string;
  shortName: string;
  leadEmail: string;
  slackChannel: string;
  defaultSlaHours: number;
  gradient: string;
  borderGlow: string;
  badgeColor: string;
  description: string;
  playbook: string[];
  publicResponse: string;
}

export const TEAM_ALIAS_MAP: Record<string, string> = {
  digital_eng_mobile: 'digital_engineering_mobile',
  digital_engineering_mobile: 'digital_engineering_mobile',
  payments_ops: 'payments_operations',
  payments_operations: 'payments_operations',
  travel_lounges_prod: 'travel_lounges_product',
  travel_lounges_product: 'travel_lounges_product',
  cafe_ops: 'cafe_operations',
  cafe_operations: 'cafe_operations',
  digital_ai_security: 'digital_ai_security',
  shopping_eng: 'shopping_engineering',
  shopping_engineering: 'shopping_engineering',
  customer_exp: 'customer_experience',
  customer_experience: 'customer_experience',
};

export const ENTERPRISE_TEAMS_CONFIG: Record<string, TeamMeta> = {
  digital_engineering_mobile: {
    id: 'digital_engineering_mobile',
    canonicalId: 'digital_engineering_mobile',
    name: 'Digital Engineering - Mobile Platform',
    shortName: 'Mobile Engineering',
    leadEmail: 'mobile-engineering@capitalone.com',
    slackChannel: '#team-mobile-eng',
    defaultSlaHours: 24,
    gradient: 'from-sky-600/30 via-blue-700/20 to-[#04162B]',
    borderGlow: 'border-sky-500/50 hover:border-sky-400',
    badgeColor: 'bg-sky-950/70 text-sky-300 border-sky-600/50',
    description: 'Owns iOS & Android core banking apps, biometrics (Face ID/Touch ID), crash prevention, and mobile deposit.',
    playbook: [
      '1. Triage Crashlytics/Sentry logs for unhandled exceptions or null dereferences.',
      '2. Reproduce user flow on physical iOS/Android test matrix matching reported OS versions.',
      '3. Verify biometric, keychain, and push notification entitlements.',
      '4. Implement defensive fallback to PIN/passcode if biometric authentication errors occur.',
      '5. Deploy hotfix build to TestFlight / internal beta channel and monitor crash-free sessions.',
    ],
    publicResponse:
      "Thank you for reporting this issue. Our mobile engineering team has identified the startup issue in the latest update and released an urgent hotfix patch. Please update your app from the store to restore normal functionality. If issues persist, reach out to mobile-support@capitalone.com.",
  },
  payments_operations: {
    id: 'payments_operations',
    canonicalId: 'payments_operations',
    name: 'Payments & Card Operations',
    shortName: 'Payments Ops',
    leadEmail: 'payments-ops@capitalone.com',
    slackChannel: '#team-payments-ops',
    defaultSlaHours: 48,
    gradient: 'from-amber-600/30 via-orange-700/20 to-[#04162B]',
    borderGlow: 'border-amber-500/50 hover:border-amber-400',
    badgeColor: 'bg-amber-950/70 text-amber-300 border-amber-600/50',
    description: 'Manages card authorization gateways, checking account fee disclosures, balance syncing, and transaction holds.',
    playbook: [
      '1. Audit payment gateway transaction logs for merchant rejection codes.',
      '2. Review clearinghouse cut-off times and pending authorization hold windows.',
      '3. Verify fee assessment logic against zero-fee checking account rules.',
      '4. Process automated fee waivers for affected cardholders in good standing.',
      '5. Update transaction ledger reconciliation service to prevent duplicate debit holds.',
    ],
    publicResponse:
      "We understand how frustrating unexpected transaction declines or fee charges can be. We are reviewing your account history to ensure fees are applied accurately according to our zero-fee checking policy. Please contact 360-support@capitalone.com for immediate account assistance.",
  },
  travel_lounges_product: {
    id: 'travel_lounges_product',
    canonicalId: 'travel_lounges_product',
    name: 'Travel & Airport Lounges Product',
    shortName: 'Travel & Lounges',
    leadEmail: 'travel-product@capitalone.com',
    slackChannel: '#team-travel-lounges',
    defaultSlaHours: 24,
    gradient: 'from-blue-600/30 via-indigo-700/20 to-[#04162B]',
    borderGlow: 'border-blue-500/50 hover:border-blue-400',
    badgeColor: 'bg-blue-950/70 text-blue-300 border-blue-600/50',
    description: 'Oversees airport lounge access policies, digital waitlist throttling, partner transfer ratios, and travel booking portal.',
    playbook: [
      '1. Review hourly lounge ingress telemetries against departing flight bank density.',
      '2. Throttle digital waitlist admission rate to preserve physical seating capacity.',
      '3. Deploy live occupancy warning banners inside Capital One Travel mobile portal.',
      '4. Coordinate with airport station managers to distribute overflow beverage vouchers.',
      '5. Audit partner airline booking sync API latencies.',
    ],
    publicResponse:
      "We sincerely apologize for the crowding you experienced during your visit. We are actively managing peak flight bank capacity and expanding live wait-time tracking in the Capital One app so cardholders can plan visits smoothly. We'd love to make this right—please contact travel-support@capitalone.com.",
  },
  cafe_operations: {
    id: 'cafe_operations',
    canonicalId: 'cafe_operations',
    name: 'Café & Branch Operations',
    shortName: 'Café Operations',
    leadEmail: 'cafe-ops@capitalone.com',
    slackChannel: '#team-cafe-ops',
    defaultSlaHours: 48,
    gradient: 'from-emerald-600/30 via-teal-700/20 to-[#04162B]',
    borderGlow: 'border-emerald-500/50 hover:border-emerald-400',
    badgeColor: 'bg-emerald-950/70 text-emerald-300 border-emerald-600/50',
    description: 'Maintains Capital One Café co-working facilities, guest Wi-Fi networks, ATM reliability, and ambassador services.',
    playbook: [
      '1. Clear guest Wi-Fi DHCP lease pool exhaustion and restart captive portal controller.',
      '2. Test access point signal strength and latency across high-occupancy seating zones.',
      '3. Audit on-site ATM cash levels and card reader diagnostics.',
      '4. Retrain café ambassadors on contactless Peet\'s beverage discount scanning.',
      '5. Coordinate facility maintenance tickets for quiet room charging stations.',
    ],
    publicResponse:
      "We're sorry your visit to our Capital One Café didn't meet expectations! We have upgraded our Wi-Fi access points to improve reliability. Next time you visit, enjoy a handcrafted beverage on us—speak with any ambassador on site.",
  },
  digital_ai_security: {
    id: 'digital_ai_security',
    canonicalId: 'digital_ai_security',
    name: 'Digital AI & Security (Eno)',
    shortName: 'Eno AI & Security',
    leadEmail: 'eno-ai@capitalone.com',
    slackChannel: '#team-eno-security',
    defaultSlaHours: 48,
    gradient: 'from-purple-600/30 via-violet-700/20 to-[#04162B]',
    borderGlow: 'border-purple-500/50 hover:border-purple-400',
    badgeColor: 'bg-purple-950/70 text-purple-300 border-purple-600/50',
    description: 'Manages Eno natural language virtual assistant, virtual card number tokenization, and fraud alert calibration.',
    playbook: [
      '1. Inspect virtual card number tokenization logs with merchant gateway networks.',
      '2. Calibrate fraud anomaly detection scoring model to reduce false-positive card locks.',
      '3. Retrain Eno NLP intent classifier for ambiguous transaction inquiries.',
      '4. Update customer-facing error messages when merchants restrict virtual BIN ranges.',
      '5. Monitor token refresh success rate across browser autocompletion flows.',
    ],
    publicResponse:
      "Security is our top priority, but we regret that your virtual card was declined at checkout. We have updated our merchant compatibility settings to prevent unexpected blocks. Please reach out to eno-support@capitalone.com if you need an immediate replacement card.",
  },
  shopping_engineering: {
    id: 'shopping_engineering',
    canonicalId: 'shopping_engineering',
    name: 'Shopping Platform Engineering',
    shortName: 'Shopping Engineering',
    leadEmail: 'shopping-eng@capitalone.com',
    slackChannel: '#team-shopping-platform',
    defaultSlaHours: 48,
    gradient: 'from-rose-600/30 via-pink-700/20 to-[#04162B]',
    borderGlow: 'border-rose-500/50 hover:border-rose-400',
    badgeColor: 'bg-rose-950/70 text-rose-300 border-rose-600/50',
    description: 'Engineers the Capital One Shopping browser extension, coupon auto-injection algorithms, and cashback affiliate attribution.',
    playbook: [
      '1. Profile content script DOM mutation observers on reported e-commerce partner domains.',
      '2. Throttle coupon code auto-injection polling intervals to 250ms to eliminate tab lockups.',
      '3. Verify affiliate cashback tracking attribution webhooks and cookie lifespans.',
      '4. Publish updated extension package v2.4.2 to Chrome Web Store.',
      '5. Run automated headless test suite across top 100 merchant checkout pages.',
    ],
    publicResponse:
      "Thanks for flagging this extension issue! We have released an update addressing browser slowdowns during checkout. Please update the extension in Chrome Web Store to enjoy automatic coupon savings without delay.",
  },
  customer_experience: {
    id: 'customer_experience',
    canonicalId: 'customer_experience',
    name: 'Customer Experience & Escalations',
    shortName: 'CX & Escalations',
    leadEmail: 'cx-leadership@capitalone.com',
    slackChannel: '#team-cx-escalations',
    defaultSlaHours: 72,
    gradient: 'from-slate-600/30 via-slate-700/20 to-[#04162B]',
    borderGlow: 'border-slate-500/50 hover:border-slate-400',
    badgeColor: 'bg-slate-800/80 text-slate-300 border-slate-600/50',
    description: 'Handles high-priority customer escalations, IVR phone queue routing, and serves as the intelligent fallback for unmatched complaints.',
    playbook: [
      '1. Review IVR phone routing tree and customer service queue hold time distributions.',
      '2. Identify recurring friction points and update customer support knowledge base articles.',
      '3. Escalate high-urgency unresolved complaints to senior resolution specialists.',
      '4. Provide proactive outreach to accounts impacted by systemic service delays.',
      '5. Track first-call resolution (FCR) rate for newly introduced product features.',
    ],
    publicResponse:
      "We sincerely apologize for the hold time you experienced. We value your time and are expanding support coverage during peak hours. A senior representative is available to assist you directly at 1-800-CAPITAL.",
  },
};

export function getTeamMeta(teamId: string): TeamMeta {
  const canonical = TEAM_ALIAS_MAP[teamId] || teamId;
  return (
    ENTERPRISE_TEAMS_CONFIG[canonical] || {
      id: teamId,
      canonicalId: canonical,
      name: teamId.replace(/_/g, ' ').toUpperCase(),
      shortName: teamId.replace(/_/g, ' '),
      leadEmail: 'operations@capitalone.com',
      slackChannel: '#general-operations',
      defaultSlaHours: 48,
      gradient: 'from-slate-700/30 to-slate-900',
      borderGlow: 'border-slate-600',
      badgeColor: 'bg-slate-800 text-slate-300 border-slate-700',
      description: 'Enterprise business operations team.',
      playbook: ['1. Triage complaint', '2. Escalate to team lead', '3. Execute standard resolution protocol.'],
      publicResponse: 'Thank you for your feedback. We are actively investigating.',
    }
  );
}
