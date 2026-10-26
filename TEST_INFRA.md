# SPREEGO End-to-End (E2E) Test Infrastructure Specification

**Specification Version**: 1.0.0  
**Target Environment**: Vitest 2.x + React Testing Library + jsdom  
**Authoritative Sources**: `ORIGINAL_REQUEST.md` (Screens 1–10, R1–R4), `PROJECT.md`, Design & Backend Analysis Specifications  
**Integrity Standard**: Opaque-box, requirement-driven, zero-facade verification  

---

## 1. Test Philosophy & Principles

### 1.1 Opaque-Box, Requirement-Driven Testing
All tests in this suite are derived strictly from the authoritative specifications in `ORIGINAL_REQUEST.md` and `PROJECT.md`. Tests interact with the application through its public boundaries—rendered DOM elements, user gesture events, route transitions, and API client request/response contracts—treating internal component mechanics as an opaque box.

### 1.2 Anti-Cheat & Test Integrity Mandate
- **No Facade Tests**: Tests must execute authentic assertions verifying DOM structure, state changes, calculation correctness, error handling, and payload structures. Tautological assertions (e.g. `expect(true).toBe(true)`) are strictly prohibited.
- **Explicit Authoritative Expected Outputs**: Every expected value is derived from the requirement documents, backend Pydantic models, or Taste-Design token specifications.
- **Isolation & Reproducibility**: Each test case sets up its own state, isolates storage and DOM mocks, and restores global spies upon completion.

---

## 2. 4-Tier Test Suite Architecture

The SPREEGO E2E test suite is organized into 4 distinct testing tiers with increasing scope:

| Tier | Focus | Minimum Target | Test Suite File |
|------|-------|----------------|-----------------|
| **Tier 1** | Feature Coverage (Screens 1–10, R1–R4) | >= 50 tests | `frontend/src/tests/e2e/tier1_feature_coverage.test.tsx` |
| **Tier 2** | Boundary & Corner Cases | >= 50 tests | `frontend/src/tests/e2e/tier2_boundary_corner.test.tsx` |
| **Tier 3** | Cross-Feature Interactions | >= 10 tests | `frontend/src/tests/e2e/tier3_cross_feature.test.tsx` |
| **Tier 4** | Real-World User Journeys | >= 5 journeys | `frontend/src/tests/e2e/tier4_real_world_scenarios.test.tsx` |

**Total Suite Size**: >= 115 comprehensive test cases.

---

## 3. Feature Inventory & Coverage Mapping

### 3.1 Requirement R1: 10-Screen Architecture Mapping

| Screen # | Screen Name | Key Elements & Behaviors Tested | Tiers Covering |
|----------|-------------|---------------------------------|----------------|
| **Screen 1** | **Home Feed (Reels Player)** | Vertical reels player, For You/Following/Clubs sub-tabs, sound mute/unmute toggle, clap reaction counter, comment drawer trigger, share modal trigger, bookmark toggle, creator overlay, sponsored badge ("SkyWings"), rotating vinyl disc & equalizer. | Tier 1, 2, 3, 4 |
| **Screen 2** | **Spree (Explore & Discovery)** | Search bar with debounced input and clear button, discovery tabs (For You, Trending, Following), media filter chips (All, Photos, Videos, Long Videos), 2-column masonry grid, thumbnail badges. | Tier 1, 2, 3 |
| **Screen 3** | **Upload / Create Modal** | Bottom sheet spring modal, 6 primary creation mode tiles (Upload Video, Upload Photo, Go Live, Create Spree, Collage, Add to Moments), 3 quick tools (Open Camera, From Gallery, Drafts), direct upload contract. | Tier 1, 2, 4 |
| **Screen 4** | **Opens (Challenges & Competitions)** | Segmented toggle (Challenges vs Competitions), Nike Move Better hero card ($50K pool), category chips (All, Creative, Fitness, Fashion, Food), active challenge cards with timers and participant counters. | Tier 1, 2, 3, 4 |
| **Screen 5** | **Challenge Details** | Cover media, title, creator attribution, 3 metrics cards (Participants, Reward Pool, Days Left), rules & guidelines, View vs Ranking toggle, Top Picks grid, Join CTA. | Tier 1, 2, 3, 4 |
| **Screen 6** | **Opens Ranking (Leaderboard)** | Live scored leaderboard, timeframe filters (Overall, Weekly, Today), Ranks 1–10+ with Gold 🥇, Silver 🥈, Bronze 🥉 badges, creator avatars, handles, score badges. | Tier 1, 2, 3, 4 |
| **Screen 7** | **Brand Sponsorship** | Tata Motors "Drive Your Story" hero banner, ₹1,00,000 reward pool, 15 days duration, top 10 winners quota, brand description, participant submission drawer. | Tier 1, 2, 3 |
| **Screen 8** | **Creator Profile** | 80px avatar with gradient ring, handle `@travelwithme`, bio, Bangalore location chip, stats row (Posts, Followers, Following), story highlights row, media tabs (Spree, Moments, Collage, Saved), post grid. | Tier 1, 2, 3 |
| **Screen 9** | **My Store (Creator Commerce)** | Catalog tabs (Products, Digital, Orders), merchandise cards with INR prices and stock indicators, ₹0 Free Community Pass card, order checkout drawer. | Tier 1, 2, 3, 4 |
| **Screen 10**| **Creator Analytics & Wallet** | 3 KPI cards (Views, Engagement, New Followers) with growth badges, 7-day views trend line chart, top-performing content list, wallet balance, UPI payout withdrawal drawer. | Tier 1, 2, 3, 4 |

### 3.2 Requirements R2, R3, R4 Mapping
- **R2 (Taste-Design System)**: Tested for calibrated palette classes (`bg-[#0B0D13]`, `bg-[#12151E]`, `text-[#F5D061]`, `bg-[#7C3AED]`), spring drawer animations, particle bursts, and typography structure.
- **R3 (User Permissions & Consent Guard)**: Initial launch blocking sheet, review of Community Guidelines, Privacy Policy, and Interaction Telemetry, local storage persistence (`spreego_consent_accepted`), rejection/revocation behavior.
- **R4 (Backend Integration & Telemetry)**: Connects to `/api/v1` endpoints, telemetry streaming on watch/skip to `POST /api/v1/sprees/{id}/view` without client-side score calculations, idempotent claps, ₹0 passes, and wallet payouts.

---

## 4. Test Suite Execution & Runner Architecture

### 4.1 Test Runner Configuration
- **Runner**: Vitest 2.1.x
- **DOM Engine**: `jsdom` 25.x with `@testing-library/react` 16.x and `@testing-library/jest-dom` 6.x
- **Config File**: `frontend/vitest.config.ts`
- **Setup File**: `frontend/src/tests/setup.ts` (Mocks `window.matchMedia`, `IntersectionObserver`, `ResizeObserver`, `HTMLMediaElement.prototype.play/pause`, `canvas-confetti`, and `localStorage`).

### 4.2 Commands to Run the Test Suite
```bash
# Run all unit and E2E tests
npm test

# Run only the E2E 4-Tier test suite
npx vitest run src/tests/e2e

# Run specific tiers
npx vitest run src/tests/e2e/tier1_feature_coverage.test.tsx
npx vitest run src/tests/e2e/tier2_boundary_corner.test.tsx
npx vitest run src/tests/e2e/tier3_cross_feature.test.tsx
npx vitest run src/tests/e2e/tier4_real_world_scenarios.test.tsx

# Run with coverage report
npx vitest run --coverage
```

---

## 5. Tier 4: Real-World Application Scenarios (Detailed Flow)

1. **Scenario 1: First-Time User Onboarding & Consent Gate Flow**
   - User launches application with fresh session.
   - Consent Guard modal renders, blocking feed interaction.
   - User reviews Guidelines, Privacy, and Telemetry disclosures.
   - User accepts terms -> Modal smoothly dismisses and sets `localStorage.setItem("spreego_consent_accepted", "true")`.
   - Feed is automatically mounted and initial Sprees are loaded.

2. **Scenario 2: Creator Content Upload & Feed Integration Flow**
   - Creator opens Upload modal via navigation dock `+` action.
   - Creator selects "Upload Video" mode.
   - Creator inputs title, tags, description, and confirms upload payload.
   - Direct upload API client endpoint is invoked.
   - Creation modal closes and newly published content is available in feed.

3. **Scenario 3: Open Challenge Discovery, Join & Leaderboard Verification Flow**
   - User navigates to Opens tab.
   - Selects featured challenge (e.g., "Travel Tales" / "Nike Move Better").
   - Reviews challenge reward pool, countdown timer, and guidelines.
   - User joins challenge -> verifies joined status.
   - User toggles to "Ranking" view -> inspects top ranked creators and verifies scores.

4. **Scenario 4: Creator Commerce Store Shopping, ₹0 Pass & Wallet Payout Flow**
   - User navigates to Creator Store.
   - Inspects featured merchandise items and stock status.
   - User activates ₹0 Creator Community Pass -> receives active membership status.
   - User inspects Creator Analytics & Wallet -> verifies available balance (₹42,500).
   - User opens Payout Drawer -> inputs UPI ID (`creator@okaxis`) -> submits payout request -> verifies ledger deduction.

5. **Scenario 5: Video Reel Playback, Engagement & Background Telemetry Stream Flow**
   - User views active video reel on Home Feed.
   - Player records watch duration.
   - Double-tap triggers clap reaction, incrementing clap count and firing particle burst.
   - User navigates to next reel -> triggers telemetry beacon dispatch to `POST /api/v1/sprees/{id}/view` with duration and completion status without client-side score modification.

