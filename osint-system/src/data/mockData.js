export const mockCase = {
  id: "CASE-2024-0847",
  subject: "Amira Benali",
  age: 14,
  lastSeen: "2024-01-15",
  location: "Casablanca, Morocco",
  description: "Last seen wearing blue jacket near Morocco Mall",
  status: "active",
  createdAt: "2024-01-15T09:30:00Z",
  priority: "critical",
  tags: ["minor", "casablanca", "mall-district"],
};

export const mockClaimClusters = [
  {
    id: "CC-001",
    label: "Morocco Mall Sighting",
    claims: [
      "Seen near Morocco Mall",
      "Girl at Morocco Mall looks like her",
      "Possible sighting Casablanca mall",
    ],
    frequency: 47,
    uniqueSources: 31,
    recentActivity: "2h ago",
    crowdScore: 0.72,
    aiVerificationScore: 0.61,
    finalScore: 0.67,
    status: "high-signal",
    sources: [
      { platform: "twitter", count: 23 },
      { platform: "reddit", count: 12 },
      { platform: "facebook", count: 8 },
      { platform: "forums", count: 4 },
    ],
    evidence: [
      { type: "text", content: "CCTV footage requested from mall", verified: true },
      { type: "image", content: "User-submitted photo - partial match", verified: false },
    ],
    contradictions: [],
    timeline: [
      { time: "14:23", event: "First mention on Twitter" },
      { time: "15:47", event: "12 corroborating posts" },
      { time: "16:30", event: "Reddit thread created" },
    ],
  },
  {
    id: "CC-002",
    label: "Train Station Movement",
    claims: [
      "Spotted at Casa-Port station",
      "Seen boarding train going north",
      "Girl matching description at station",
    ],
    frequency: 18,
    uniqueSources: 14,
    recentActivity: "5h ago",
    crowdScore: 0.48,
    aiVerificationScore: 0.39,
    finalScore: 0.44,
    status: "medium-signal",
    sources: [
      { platform: "twitter", count: 10 },
      { platform: "facebook", count: 5 },
      { platform: "forums", count: 3 },
    ],
    evidence: [
      { type: "text", content: "Station CCTV analysis pending", verified: false },
    ],
    contradictions: [
      { content: "Timestamp conflicts with Mall sighting", severity: "medium" },
    ],
    timeline: [
      { time: "16:00", event: "Initial report posted" },
      { time: "17:20", event: "Secondary confirmation" },
    ],
  },
  {
    id: "CC-003",
    label: "Rabat Sighting",
    claims: [
      "Spotted in another city - Rabat",
      "Someone saw her in Agdal district",
      "Photo circulating from Rabat",
    ],
    frequency: 89,
    uniqueSources: 12,
    recentActivity: "3h ago",
    crowdScore: 0.21,
    aiVerificationScore: 0.08,
    finalScore: 0.14,
    status: "misinformation",
    misinfoReason: "Image reused from 2022 missing persons case",
    botAmplification: true,
    sources: [
      { platform: "twitter", count: 67 },
      { platform: "tiktok", count: 22 },
    ],
    evidence: [],
    contradictions: [
      { content: "Image traced to 2022 case #CASE-2022-0341", severity: "critical" },
      { content: "75% of accounts posting are <30 days old", severity: "high" },
    ],
    timeline: [
      { time: "13:00", event: "Viral spread begins" },
      { time: "14:30", event: "Bot amplification detected" },
      { time: "15:00", event: "Flagged as misinformation" },
    ],
  },
  {
    id: "CC-004",
    label: "Ain Diab Beach Area",
    claims: [
      "Seen walking near Ain Diab",
      "Possible sighting corniche area",
      "Someone spotted her near the beach",
    ],
    frequency: 9,
    uniqueSources: 8,
    recentActivity: "1h ago",
    crowdScore: 0.34,
    aiVerificationScore: 0.29,
    finalScore: 0.31,
    status: "low-signal",
    sources: [
      { platform: "twitter", count: 5 },
      { platform: "reddit", count: 4 },
    ],
    evidence: [],
    contradictions: [],
    timeline: [
      { time: "17:45", event: "Single post, no corroboration yet" },
    ],
  },
];

export const mockLeads = [
  {
    id: "LEAD-001",
    claimId: "CC-001",
    title: "Morocco Mall — High Confidence Sighting",
    confidence: 0.67,
    priority: "urgent",
    evidence: [
      "47 independent mentions across 4 platforms",
      "31 unique user accounts reporting",
      "No major contradictions found",
      "Temporal consistency with last known location",
    ],
    actionRequired: "Request mall CCTV footage for Jan 15, 14:00-18:00",
    assignedTo: null,
    createdAt: "2024-01-15T18:00:00Z",
  },
  {
    id: "LEAD-002",
    claimId: "CC-002",
    title: "Casa-Port Station — Medium Signal",
    confidence: 0.44,
    priority: "medium",
    evidence: [
      "18 mentions, 14 unique sources",
      "Timing conflict with Mall sighting (investigate)",
      "Station records obtainable via formal request",
    ],
    actionRequired: "Cross-check timestamp with Morocco Mall cluster",
    assignedTo: null,
    createdAt: "2024-01-15T19:30:00Z",
  },
];

export const mockGraphNodes = [
  { id: "subject", label: "Amira Benali", type: "subject", x: 400, y: 250 },
  { id: "CC-001", label: "Morocco Mall\nSighting", type: "cluster-high", x: 200, y: 120 },
  { id: "CC-002", label: "Train Station\nMovement", type: "cluster-medium", x: 600, y: 120 },
  { id: "CC-003", label: "Rabat\nSighting", type: "cluster-misinfo", x: 200, y: 380 },
  { id: "CC-004", label: "Ain Diab\nBeach", type: "cluster-low", x: 600, y: 380 },
  { id: "E-001", label: "Mall CCTV\nRequest", type: "evidence", x: 80, y: 60 },
  { id: "E-002", label: "User Photo\n(unverified)", type: "evidence-unverified", x: 100, y: 200 },
  { id: "CONTRA-001", label: "2022 Case\nImage Reuse", type: "contradiction", x: 100, y: 420 },
];

export const mockGraphEdges = [
  { from: "subject", to: "CC-001", label: "possible sighting", type: "sighting" },
  { from: "subject", to: "CC-002", label: "possible sighting", type: "sighting" },
  { from: "subject", to: "CC-003", label: "false claim", type: "misinfo" },
  { from: "subject", to: "CC-004", label: "low signal", type: "low" },
  { from: "CC-001", to: "E-001", label: "verified by", type: "evidence" },
  { from: "CC-001", to: "E-002", label: "supported by", type: "evidence" },
  { from: "CC-003", to: "CONTRA-001", label: "contradicted by", type: "contradiction" },
];

export const mockChatHistory = [
  {
    role: "system",
    content: "OSINT Intelligence Agent initialized for Case CASE-2024-0847. I have analyzed 163 social media posts, extracted 4 claim clusters, and identified 2 high-priority leads.",
    timestamp: "18:00",
  },
  {
    role: "user",
    content: "What is the most credible crowd hypothesis?",
    timestamp: "18:01",
  },
  {
    role: "assistant",
    content: "The **Morocco Mall Sighting** (CC-001) is your highest-confidence hypothesis with a final score of **0.67**.\n\n**Why it ranks highest:**\n- 47 independent mentions from 31 unique accounts\n- High source diversity (Twitter, Reddit, Facebook, Forums)\n- No significant contradictions detected\n- Temporal consistency with last known location\n\n**Crowd Score:** 0.72 | **AI Verification:** 0.61\n\n**Recommended action:** Immediately request mall CCTV for Jan 15, 14:00–18:00. This is time-sensitive.",
    timestamp: "18:01",
    relatedClaim: "CC-001",
  },
  {
    role: "user",
    content: "Why is the Rabat sighting considered misinformation?",
    timestamp: "18:03",
  },
  {
    role: "assistant",
    content: "The **Rabat Sighting** (CC-003) was flagged as **likely misinformation** for two critical reasons:\n\n🚨 **Image Reuse Detected**\nThe photo circulating was reverse-image-matched to Case #CASE-2022-0341 — a completely unrelated missing persons case from 2022. The same image was used.\n\n🤖 **Bot Amplification**\n75% of the 89 accounts sharing this content were created less than 30 days ago, showing coordinated inauthentic behavior.\n\n**Despite having the highest raw engagement (89 posts), this cluster has the lowest final score (0.14)** — exactly why raw crowd signals alone are unreliable.\n\nThis is a textbook case of viral misinformation that could waste investigative resources. It has been deprioritized.",
    timestamp: "18:03",
    relatedClaim: "CC-003",
  },
];

export const mockStats = {
  totalPosts: 163,
  claimsExtracted: 4,
  clustersFormed: 4,
  highSignalLeads: 2,
  misinfoFiltered: 1,
  platformBreakdown: [
    { platform: "Twitter/X", count: 105, percentage: 64 },
    { platform: "Reddit", count: 28, percentage: 17 },
    { platform: "Facebook", count: 18, percentage: 11 },
    { platform: "TikTok", count: 7, percentage: 4 },
    { platform: "Forums", count: 5, percentage: 3 },
  ],
  processingSteps: [
    { step: "Community Ingestion", status: "complete", time: "14:30" },
    { step: "Claim Extraction", status: "complete", time: "14:45" },
    { step: "Claim Clustering", status: "complete", time: "15:00" },
    { step: "Credibility Scoring", status: "complete", time: "15:20" },
    { step: "AI Verification", status: "complete", time: "16:00" },
    { step: "Misinformation Filter", status: "complete", time: "16:15" },
    { step: "Lead Generation", status: "complete", time: "16:30" },
    { step: "Graph Update", status: "complete", time: "16:35" },
  ],
};
