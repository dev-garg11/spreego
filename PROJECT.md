# Project: SPREEGO Production-Grade Frontend

## Architecture
- **Framework**: Vite + React 18/19 + TypeScript + Tailwind CSS.
- **Visual Design System**: Senior human-crafted Taste-Design specification. Calibrated deep zinc/charcoal palette (`#0B0D13`, `#12151E`, `#1A1F2C`) with electric violet (`#7C3AED`) and warm champagne (`#F5D061`) accents. Strictly zero generic AI-slop clichés.
- **Motion & Physics Engine**: `framer-motion` for kinetic reel snap, spring bottom-sheet drawers, rotating vinyl disc with soundwave equalizer, and sliding pill indicators; `canvas-confetti` for tactile double-tap clap particle bursts.
- **Data Visualization**: `recharts` for 7-day interactive line chart trend in Creator Analytics.
- **Iconography**: `lucide-react` for crisp SVG icons.
- **Testing Toolchain**: `vitest` + `@testing-library/react` + `@testing-library/jest-dom` + `jsdom`.
- **Backend Integration**: Direct connection to live FastAPI backend (`http://localhost:8000/api/v1/` and `/auth/`) with Vite proxy and high-fidelity mock fallback data ensuring graceful resilience.
- **Client Architecture**:
  - `src/api/`: Typed API client covering feed, engagement, opens, products, memberships, wallet, users, and telemetry streaming.
  - `src/components/common/`: Navigation shell, BottomBar, TopBar, ConsentGuard modal, Toast, Drawer, Button, Tabs.
  - `src/components/feed/`: ReelPlayer, ReelItem, RightRail, CreatorOverlay, CommentDrawer, ShareModal, VinylDisc.
  - `src/components/spree/`: SpreeExplore, MasonryGrid, CategoryChips, SearchBar.
  - `src/components/upload/`: UploadModal, CreationGrid, FileUploadDropzone.
  - `src/components/opens/`: OpensFeed, HeroChallengeCard, ChallengeDetails, RankingLeaderboard, BrandSponsorship.
  - `src/components/creator/`: CreatorProfile, StoryHighlights, MediaTabs, StoreCatalog, ProductCard, CommunityPassModal, CreatorAnalytics, TrendChart, WalletDrawer.
  - `src/hooks/`: `useTelemetry`, `useClaps`, `useFeed`, `useOpens`, `useWallet`, `useConsent`.
  - `src/context/`: AuthContext, ConsentContext, AudioContext.

## Code Layout
```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── vitest.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── types/
│   │   ├── index.ts
│   │   ├── spree.ts
│   │   ├── open.ts
│   │   ├── store.ts
│   │   ├── wallet.ts
│   │   └── user.ts
│   ├── api/
│   │   ├── client.ts
│   │   ├── mockData.ts
│   │   ├── feedApi.ts
│   │   ├── opensApi.ts
│   │   ├── storeApi.ts
│   │   ├── walletApi.ts
│   │   └── telemetryApi.ts
│   ├── context/
│   │   ├── AppContext.tsx
│   │   └── ConsentContext.tsx
│   ├── hooks/
│   │   ├── useTelemetry.ts
│   │   └── useHapticClap.ts
│   ├── components/
│   │   ├── shell/
│   │   │   ├── BottomNav.tsx
│   │   │   ├── TopNav.tsx
│   │   │   └── ConsentGuardModal.tsx
│   │   ├── feed/
│   │   │   ├── ReelFeed.tsx
│   │   │   ├── ReelCard.tsx
│   │   │   ├── CommentDrawer.tsx
│   │   │   ├── VinylDisc.tsx
│   │   │   └── ParticleBurst.tsx
│   │   ├── spree/
│   │   │   ├── SpreeExplore.tsx
│   │   │   └── MasonryGrid.tsx
│   │   ├── upload/
│   │   │   └── UploadSheetModal.tsx
│   │   ├── opens/
│   │   │   ├── OpensOverview.tsx
│   │   │   ├── ChallengeDetails.tsx
│   │   │   ├── RankingLeaderboard.tsx
│   │   │   └── BrandSponsorship.tsx
│   │   └── creator/
│   │       ├── CreatorProfile.tsx
│   │       ├── StoreCatalog.tsx
│   │       ├── ProductCard.tsx
│   │       ├── PassSubscriptionModal.tsx
│   │       ├── AnalyticsDashboard.tsx
│   │       ├── TrendChart.tsx
│   │       └── WalletDrawer.tsx
│   └── tests/
│       ├── setup.ts
│       ├── unit/
│       └── e2e/
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Taste-Design System & Tokens | Calibrated dark palette (#0B0D13, #12151E, #1A1F2C), violet & champagne accents | M1 | Survey / R2 |
| 2 | Vite + React + TS Scaffolding | Bundler, TypeScript configs, PostCSS, Tailwind config with tokens | M1 | Survey / R1 |
| 3 | Core Navigation Shell & Bottom Bar | Bottom nav with 5 tabs (Home, Spree, Upload, Opens, Profile), active indicators | M1 | Survey / R1 |
| 4 | R3 Terms & Consent Guard Modal | Initial launch consent gate, community guidelines, telemetry notice, storage persistence | M1 | Survey / R3 |
| 5 | Shared API Client & Fallback Engine | HTTP client pointing to /api/v1 with mock fallback data for offline resilience | M1 | Survey / R4 |
| 6 | Unit & Component Test Harness | Vitest + Testing Library test runner setup | M1 | Survey |
| 7 | Screen 1: Reel Video Player | Vertical full-screen reels with auto-loop, pause/play, sound toggle | M2 | Survey / R1 |
| 8 | Screen 1: Kinetic Reel Snap | Fluid vertical scrolling with spring inertia snap | M2 | Survey / R2 |
| 9 | Screen 1: Tactile Double-Tap Clap | Double tap to clap with haptic particle burst and counter increment | M2 | Survey / R2 |
| 10 | Screen 1: Right-Rail Engagement Controls | Clap count, comment drawer trigger, share modal, bookmark/save toggle | M2 | Survey / R1 |
| 11 | Screen 1: Comment Spring Drawer | Smooth bottom-sheet drawer with blur backdrop, comments list, new comment input | M2 | Survey / R2 |
| 12 | Screen 1: Rotating Vinyl Disc & Equalizer | Spinning vinyl audio disc with live soundwave equalizer animation | M2 | Survey / R2 |
| 13 | Screen 1: Creator Overlay & Sponsor Badge | Creator handle, caption, music tag, and sponsored SkyWings campaign badge | M2 | Survey / R1 |
| 14 | Screen 1: Telemetry Streaming Hook | Watch duration and skip telemetry to POST /api/v1/sprees/{id}/view without client math | M2 | Survey / R4 |
| 15 | Screen 2: Spree Explore Search Bar | Real-time search bar with clear button and query filtering | M2 | Survey / R1 |
| 16 | Screen 2: Discovery Feed Tabs | Sliding pill tabs: For You, Trending, Following | M2 | Survey / R1 |
| 17 | Screen 2: Media Type Filter Chips | Filter chips: All, Photos, Videos, Long Videos | M2 | Survey / R1 |
| 18 | Screen 2: 2-Column Masonry Media Grid | Responsive 2-column masonry layout with creator tags, badges, and view counts | M2 | Survey / R1 |
| 19 | Screen 3: Upload Modal Bottom Sheet | Spring bottom-sheet modal drawer with backdrop blur | M2 | Survey / R1 |
| 20 | Screen 3: 6-Option Creation Grid | Upload Video, Upload Photo, Go Live, Create Spree, Collage, Moments | M2 | Survey / R1 |
| 21 | Screen 3: Quick Creation Tools | Open Camera capture, Gallery picker, Drafts quick launcher | M2 | Survey / R1 |
| 22 | Screen 3: Direct Upload Contract | Connection to POST /api/v1/uploads/direct and POST /api/v1/sprees | M2 | Survey / R4 |
| 23 | Screen 4: Opens Mode Segmented Toggle | Smooth sliding segmented controller between Challenges and Competitions | M3 | Survey / R1 |
| 24 | Screen 4: Featured Hero Challenge Carousel | Nike Move Better Challenge hero card with $50K reward pool, countdown | M3 | Survey / R1 |
| 25 | Screen 4: Category Filter Chips | Category chips (Fitness, Dance, Gaming, Tech, Music) | M3 | Survey / R1 |
| 26 | Screen 4: Active Challenges Card List | Active challenges list with participant counters, prize pools, time remaining | M3 | Survey / R1 |
| 27 | Screen 5: Challenge Details Header & Stats | Cover hero, creator attribution, participants, reward pool, days left | M3 | Survey / R1 |
| 28 | Screen 5: Rules & Guidelines Section | Challenge description, eligibility, submission rules | M3 | Survey / R1 |
| 29 | Screen 5: View vs Ranking Segmented Controller | Sliding pill controller switching between submissions feed and leaderboard | M3 | Survey / R1 |
| 30 | Screen 5: Top Submissions Grid | Media grid showing approved challenge submissions | M3 | Survey / R1 |
| 31 | Screen 5: Join Challenge Flow & CTA | Join CTA with modal for selecting/uploading a spree submission | M3 | Survey / R1 |
| 32 | Screen 6: Opens Ranking Filter Tabs | Real-time filter tabs: Overall, Weekly, Today | M3 | Survey / R1 |
| 33 | Screen 6: Real-Time Dynamic Leaderboard | Ranks 1 to 10+ with creator avatars, handles, score badges, thumbnails | M3 | Survey / R1 |
| 34 | Screen 7: Brand Sponsorship Hero Card | Tata Motors "Drive Your Story" hero banner, ₹1,00,000 reward pool | M3 | Survey / R1 |
| 35 | Screen 7: Campaign Details & Top 10 Rewards | Campaign duration (15 days), winner tier breakdown, sponsor overview | M3 | Survey / R1 |
| 36 | Screen 7: Participant Submission Flow | Join campaign CTA, submission requirements, terms agreement | M3 | Survey / R1 |
| 37 | Screen 8: Creator Profile Header | Avatar with gradient ring, handle, bio, location, edit/follow button | M4 | Survey / R1 |
| 38 | Screen 8: Creator Stats Row | Posts count (248), Followers (12.4K), Following (432) | M4 | Survey / R1 |
| 39 | Screen 8: Story Highlights Row | Circular story highlight bubbles with custom covers | M4 | Survey / R1 |
| 40 | Screen 8: Profile Media Tabs | Sliding pill tabs: Spree, Moments, Collage, Saved | M4 | Survey / R1 |
| 41 | Screen 8: Profile Post Grid | 3-column media grid with reel badges, view counts, and click-to-play | M4 | Survey / R1 |
| 42 | Screen 9: My Store Product Catalog Tabs | Category tabs: Products, Digital, Orders | M4 | Survey / R1 |
| 43 | Screen 9: Featured Merchandise Cards | Product cards with images, INR pricing, stock indicators, and buy flow | M4 | Survey / R1 |
| 44 | Screen 9: ₹0 Free Community Pass Modal | Creator community pass banner with instant ₹0 subscription activation | M4 | Survey / R1 |
| 45 | Screen 9: Order Checkout & Confirmation | Simple checkout drawer and order history tracking | M4 | Survey / R1 |
| 46 | Screen 10: Performance KPI Cards | Views (248.6K), Engagement (18.4K), New Followers (2.3K) with % changes | M4 | Survey / R1 |
| 47 | Screen 10: 7-Day Interactive Line Chart Trend | Interactive Recharts area/line trend chart with tooltips and date points | M4 | Survey / R1 |
| 48 | Screen 10: Top-Performing Content List | Ranked list of creator's highest-performing sprees with view/clap metrics | M4 | Survey / R1 |
| 49 | Screen 10: Creator Wallet & Payout Drawer | Reconciled ledger balance, pending payouts, instant UPI payout drawer | M4 | Survey / R1 |
| 50 | Tier 1 E2E Feature Coverage Suite | >= 50 automated tests verifying each feature in isolation | M5 | E2E Track |
| 51 | Tier 2 E2E Boundary & Corner Suite | >= 50 boundary/corner tests (empty lists, out-of-stock, errors, telemetry) | M5 | E2E Track |
| 52 | Tier 3 E2E Cross-Feature Pairwise Suite | >= 10 cross-feature tests (feed to challenge, join to leaderboard, store to wallet) | M5 | E2E Track |
| 53 | Tier 4 E2E Real-World Application Suite | >= 5 comprehensive user journey workflows | M5 | E2E Track |
| 54 | Tier 5 Adversarial Coverage Hardening | White-box stress testing, chaos/regression tests, edge case hardening | M5 | Implementation |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Foundation & Shell | Vite+React+TS setup, Tailwind taste-design tokens, App shell, BottomNav, ConsentGuard (R3), API client layer (Features 1-6) | none | PLANNED |
| M2 | Reels Engine & Discovery | Screen 1 (Home Feed, sound, claps, comments, vinyl disc, telemetry R4), Screen 2 (Spree Explore), Screen 3 (Upload Modal) (Features 7-22) | M1 | PLANNED |
| M3 | Opens, Challenges & Sponsorships | Screen 4 (Opens), Screen 5 (Challenge Details), Screen 6 (Ranking Leaderboard), Screen 7 (Brand Sponsorship) (Features 23-36) | M1 | PLANNED |
| M4 | Creator Profile, Store & Wallet | Screen 8 (Profile), Screen 9 (My Store & ₹0 Pass), Screen 10 (Analytics Chart & Wallet Drawer) (Features 37-49) | M1 | PLANNED |
| M5 | Final Milestone: 100% E2E Pass & Hardening | Phase 1: 100% pass on Tiers 1-4 E2E Test Suite from TEST_READY.md. Phase 2: Tier 5 Adversarial coverage hardening (Features 50-54) | M2, M3, M4, TEST_READY | PLANNED |

## Parallel E2E Testing Track
- **Role**: Independent, opaque-box test suite derivation directly from `ORIGINAL_REQUEST.md`.
- **Deliverables**: `TEST_INFRA.md`, test runner, test cases for Tiers 1-4 (>= 115 tests), and `TEST_READY.md`.

## Interface Contracts
### Shell ↔ Screen Modules
- `currentTab`: `'home' | 'spree' | 'upload' | 'opens' | 'profile'`
- `openModal`: `(modalType: string, payload?: any) => void`
- `activeSpreeId`: `string | null`
- `userConsent`: `{ accepted: boolean, timestamp: string }`

### Feed ↔ Telemetry Engine
- `useTelemetry(spreeId: string)`:
  - `recordWatchDuration(seconds: number)`
  - `recordSkip(spreeId: string)`
  - Automatically dispatches to `POST /api/v1/sprees/{id}/view` without client math.

### Opens ↔ Leaderboard
- `GET /api/v1/opens/{id}/ranking` -> `items: Array<{ rank: number, user_id: string, username: string, avatar: string, score: number, spree_thumbnail: string }>`

### Store ↔ Membership & Orders
- `POST /api/v1/memberships/subscribe` -> `{ plan_id: string }` -> `status: "ACTIVE"`
- `POST /api/v1/orders` -> `{ product_id: string, quantity: number }`

### Analytics ↔ Wallet
- `GET /api/v1/wallet` -> `{ available_balance: number, currency: string, pending_payout_balance: number }`
- `POST /api/v1/wallet/payout` -> `{ amount: number, payout_method: { upi_id: string } }`
