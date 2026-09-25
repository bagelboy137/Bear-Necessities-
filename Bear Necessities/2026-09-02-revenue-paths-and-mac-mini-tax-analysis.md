# Revenue paths for the Bear Necessities app + the Mac mini tax question

Created 2026-09-02. Written in response to Conor's ask: "get the Mac mini, see if
there's a way to generate revenue with the app I've made so I can pay for the Mac
mini through the business and offset some profits, act as a startup tax expert."

**Two disclaimers up front, both load-bearing:**

1. **This is information to take to a CPA, not advice to act on.** The tax section
   below lays out the current rules and the questions they raise. It does not tell
   you what to do, and you should not file anything based on it. Rules cited are
   current as of 2026 tax year to the best of a September 2026 web check; every
   figure should be reconfirmed by a professional against your actual return.
2. **The premise has a hole in it, and it's the whole thing.** A deduction offsets
   *profit*. Bear Necessities has no revenue, so there is no profit to offset.
   Buying a $2,900 machine does not save you $2,900 — at your marginal rate a
   deduction is worth roughly `cost × marginal rate`, and only if the loss is
   usable at all. The Mac mini does not become free, or even cheap, by routing it
   "through the business." More on this below; it leads Part 2.

---

## What the app and the business actually are (as of today)

Establishing the facts the analysis rests on, from the project files:

| Thing | Status |
|---|---|
| **The "app"** | A single-page Next.js / OpenAI Sites marketing site (`website/`), deployed **owner-only / private** at `bear-necessities-overland.cmkennedy218.chatgpt.site`. Ten CAD module cards, function filters, an interactive four-module "trip kit" builder, three concept trip routes. |
| **What it sells** | Nothing. No cart, no checkout, no pre-order, no email capture, no payment integration. It is a brochure, not a store. |
| **The product** | A modular overland camp system — bolt-together 1" aluminium extrusion cubes, ten modules designed. **Concept CAD only. Nothing ordered. No physical prototype. No supplier quote. No prices anywhere in the BOM.** |
| **Open product blocker** | C-02, the vehicle floor bracket, is unresolved (per-vehicle SKUs vs. universal L-track vs. Goose-Gear-style plate). |
| **Business entity** | None on record. `CLAUDE.md` still lists "Registered as a business?" as an open question. |
| **Trademark** | None. "Bear Necessities" is a common pun, likely in use elsewhere; a search is still outstanding. |
| **Customers / revenue** | Zero. Ever. |
| **Team** | Solo (assumed; also still an open question in `CLAUDE.md`). |
| **Time invested** | Substantial — CAD family, BOM, render pipeline, website, competitor research. All design-stage. |

So "generate revenue with the app" is really "generate revenue for Bear
Necessities," where the app's only possible role is storefront or lead capture.
There is no software product here to monetize on its own.

---

# PART 1 — Revenue paths for the app

Ordered by how close they are to a first dollar. For each: what it takes, rough
time to first dollar, plausible earnings at your likely scale (solo, no existing
audience).

### The honest headline

**Meaningful revenue in the near term is unlikely.** The product you'd actually
sell doesn't physically exist, isn't priced, and has an unresolved mounting
problem. The one asset that *is* finished — the CAD and cut lists — is sellable,
but into a niche within a niche, and only with an audience you haven't built yet.
Everything with real upside needs either capital (a prototype, then inventory or a
proven drop-ship pipeline) or an audience (YouTube / Instagram / forum presence).
You have neither today. Budget months, not weeks, before Bear Necessities clears a
dollar of profit — and quite possibly it never does, which is a fine outcome for a
project you enjoy.

### 1. Sell the build plans as a digital product — *most realistic near-term*

- **What it is:** Package what already exists — the DXF for C-01, the two-cut-length
  frame cut list, the OTS BOM with real part numbers, an assembly guide — as a
  downloadable "build your own overland module" pack. Sell on the site (Stripe
  Payment Link or Gumroad/Lemon Squeezy embed) or on Etsy.
- **What it takes:** A weekend. Write the assembly guide (the hardest part —
  you'd be committing to a design you haven't built), export a clean PDF + DXF
  bundle, wire one payment link, make the site public. No entity strictly required
  to start, though see Part 2.
- **Time to first dollar:** 1–3 weeks if you push it.
- **Plausible earnings:** Small. $20–80 per pack. Without traffic, `$0–a few
  hundred dollars total`. If a post lands in r/overlanding or an overland YouTuber
  mentions it, maybe `$50–500/mo` for a few months, then decay. This is a
  supplement, not an income.
- **Honest risk:** You'd be selling plans for a rig you've never assembled. If the
  frame or C-01 load case is wrong, that's now other people's money and safety.

### 2. Affiliate / content site off the BOM

- **What it is:** Make the site public as a build-guide resource. Every part in the
  BOM (TNUTZ/8020 extrusion, the fridge, drawer slides, power stations) gets an
  affiliate link — Amazon Associates plus any supplier programs.
- **What it takes:** Publish the site, apply to affiliate programs, write 3–5 real
  build articles. Ongoing content effort to get traffic.
- **Time to first dollar:** Weeks to first click; real money never, without traffic.
- **Plausible earnings:** `$0–$30/mo` until the site has hundreds of visitors a
  week. Overland gear has decent commission rates but you're competing with
  established channels.

### 3. One-off custom builds / local commissions

- **What it is:** Build modules to order for other overlanders in the Philly / mid-
  Atlantic scene. Cash, low volume, high touch.
- **What it takes:** Build one real module first (your own Escalade rig doubles as
  the demo — cross-links to `Escalade Work`). Then find buyers via local overland
  groups, Instagram, meetups.
- **Time to first dollar:** Whenever you have one built module and one buyer —
  could be this fall if you commit to the prototype.
- **Plausible earnings:** Thin. Maybe `$150–400 profit` per module after materials
  and your time, and you can build maybe one every week or two around a full-time
  job. Call it `$300–800/mo` if you stay busy, which you won't consistently.
- **Upside:** It's the cheapest way to validate that anyone will pay for this at
  all, and it produces the content and testimonials paths 1, 2, and 5 need.

### 4. Pre-orders / deposits on the modules

- **What it is:** Take refundable deposits (say $100–250) via the site to gauge and
  fund demand before committing to a production run.
- **What it takes:** Stripe, a clear refund policy, and — critically — enough
  confidence in your delivered cost and timeline that you're not taking money you
  can't honor. You do not have that confidence yet (no prototype, no supplier
  terms, C-02 open).
- **Time to first dollar:** Weeks, technically.
- **Plausible earnings:** Deposits aren't revenue, they're a liability until you
  ship. Realistically `0–5 deposits` from a standing start with no audience.
- **Honest risk:** Taking pre-orders for an unprototyped product with no
  fulfillment path is how indie hardware projects generate refund demands and
  reputational damage. Don't do this before a working prototype and real costs.

### 5. Audience first (YouTube / Instagram), monetize later

- **What it is:** Document building the rig on your own vehicle. This is how every
  overland brand in your competitor folder actually started (Coastal Mountain
  Vanworks, etc.) — content built the customer base, product sales followed.
- **What it takes:** Consistent content production for 12+ months. A different
  skill and time commitment than engineering.
- **Time to first dollar:** 12–24 months to ad revenue or a customer base worth
  selling to.
- **Plausible earnings:** Nothing for a year, then it depends entirely on whether
  the content is good and consistent. Most channels never clear beer money.

### 6. Full product business — drop-ship or small-batch

- **What it is:** The actual plan on the product sheet. Order frames cut to length,
  source the OTS parts, assemble or drop-ship, sell finished modules or kits.
- **What it takes:** Resolve C-02. Build and field-test a prototype. Get real
  supplier quotes and drop-ship terms (`SUPPLIER-RFQ-DRAFT.md` is drafted, unsent).
  Price it. Working capital for inventory or a validated drop-ship pipeline. An
  entity, insurance (product liability on a load-bearing vehicle rig is not
  optional), and a real storefront.
- **Time to first dollar:** 6–12+ months and real money in.
- **Plausible earnings:** Genuinely unknown. Could be a `$20–60k/yr` side business
  if the product and marketing land; could be a garage full of unsold extrusion.
  This is the ambition, but it's not a near-term revenue path — it's a business
  you'd have to decide to build.

### What I'd actually expect

If you did paths 1 and 3 in parallel this fall — package the plans, build one real
module, sell a couple of commissions — you might see **a few hundred dollars over
the next six months**, against materials cost and a lot of your evenings. That is
the realistic ceiling absent an audience or a capital commitment. It is not enough
to make the tax conversation below do anything for you.

---

# PART 2 — The tax question

**Everything in this section is for your CPA. It is not advice, and nothing here
should drive a filing decision.** Tax law changed materially in 2025 (the "One Big
Beautiful Bill Act," OBBBA) and several points below are contested or new enough
that a professional should confirm them against your return.

## 2.1 The point that comes first: a deduction is not a rebate

You wrote "offset some profits." **There are no profits.** Bear Necessities has
never had revenue. Walk through what a deduction actually does:

- A business deduction reduces **taxable income**. If the activity earns $0 and you
  deduct a $2,900 computer, you have created a **$2,900 loss**, not a $2,900
  saving.
- Whether that loss does anything depends on (a) whether it's a real business or a
  hobby — see 2.4, this is the live risk — and (b) whether the loss is usable
  against your other income — see 2.6.
- **Best case**, the loss is a real business loss and fully deductible against your
  W-2 income. Then it's worth `loss × marginal rate`. Your combined marginal rate
  is roughly:
  - Federal: ~22–24% (single or MFJ, depending on household income)
  - Pennsylvania: 3.07% flat
  - Philadelphia: you live in Chestnut Hill, so city taxes apply — resident wage
    tax ~3.75%, and a real business would owe Philadelphia BIRT / Net Profits Tax
  - **Call it ~28–31% all-in.**
- So a **$2,900 deduction saves you roughly $810–$900**. You still bear
  **~$2,000–$2,100** of the cost yourself.
- The machine is the [18-core M5 Pro / 64GB Mac mini from the Mac Mini Setup
  project](../Mac%20Mini%20Setup/), $2,899 retail (or $2,679 education). Routing it
  "through the business" changes that number by at most ~$800, in the best case,
  in a year you may not even be able to use the loss.

**If revenue doesn't plausibly arrive, the tax rationale for buying this through
the business largely evaporates.** Buy the Mac mini because you want an always-on
machine to run Claude and the CAD agent — that's a real reason and it's fine. Just
don't tell yourself the business is paying for it.

## 2.2 If there *were* a business: how a computer gets deducted

Four mechanisms, and which one applies matters:

| Mechanism | 2026 status | Catch for you |
|---|---|---|
| **De minimis safe harbor** — Reg. §1.263(a)-1(f) | Expense tangible property up to **$2,500 per item / per invoice** (no applicable financial statement). Requires a written accounting policy in place **at the start of the year** and an election statement on a timely-filed return. | **The Mac mini at ~$2,900 exceeds $2,500, so it does not qualify as a single item.** A sub-$2,500 configuration would. This is otherwise the simplest route for one computer. |
| **Section 179 expensing** | Limit $2,560,000 for 2026; now permanent, inflation-indexed. | **§179 cannot create or increase a loss.** It's limited to the business's net income. With $0 revenue, §179 gives you **nothing this year** — it carries forward. |
| **Bonus depreciation** | **100%, made permanent** by OBBBA §70301 for property acquired and placed in service after **January 19, 2025** (the scheduled phase-down to 40% then 0% was repealed). | Bonus **can** create a loss, unlike §179. But then you're back to 2.4 (hobby) and 2.6 (is the loss usable). |
| **Regular MACRS depreciation** | Computers are 5-year property. | Spreads the deduction over ~6 tax years. Slowest, but doesn't depend on current income. |

## 2.3 Business-use percentage and substantiation

- **Computers are no longer "listed property."** The TCJA removed them effective
  2018. The strict listed-property substantiation regime and the >50%-business-use
  test **no longer apply** to a computer.
- **Business-use percentage still governs the deduction.** You deduct the
  business-use fraction only. If the Mac mini is 60% business and 40% personal
  (running your own media, personal projects, family use), you deduct 60% of
  whatever mechanism above applies.
- **Mixed use of a home computer** must be allocated by a reasonable method, and
  you should keep **contemporaneous records** — a usage log, calendar entries,
  project notes — showing the business use. "It's mostly for the business" is not
  substantiation. This matters more, not less, when the activity has no revenue,
  because it's the first thing an examiner asks about.
- A machine that also runs the Fusion CAD agent, your personal projects, and
  general household computing is going to land well under 100% business, which
  further shrinks the already-small deduction.

## 2.4 Hobby loss rules — IRC §183 — the actual risk here

**An activity with no revenue, years of losses, and a large equipment deduction is
the textbook fact pattern the IRS scrutinizes under §183.** If Bear Necessities is
deemed "an activity not engaged in for profit":

- **Hobby expenses are effectively not deductible.** Miscellaneous itemized
  deductions are suspended (TCJA, and OBBBA made the suspension permanent). One
  2026 commentary claims OBBBA introduced a narrow "deduct hobby expenses up to 90%
  of hobby income" rule — **this is not well established; have your CPA verify it.**
  Either way, with $0 hobby income there's nothing to deduct against.
- **Hobby income is still fully taxable** if you later earn any.
- Net effect: the deduction you're counting on **disappears** if the activity is a
  hobby.

**The §183 nine-factor profit-motive test** (Treas. Reg. §1.183-2(b)), weighed
qualitatively, no single factor decisive:

1. **How you carry on the activity** — businesslike records, separate bank account,
   a written business plan, adjusting methods to improve profitability.
2. **Your expertise, or your advisers'** — and whether you consulted people who
   know how to make this kind of venture profitable (not just the engineering).
3. **Time and effort you put in** — substantial, though "around a full-time job"
   cuts both ways.
4. **Expectation that assets appreciate** — weak here; extrusion and CAD files
   don't appreciate.
5. **Your success in other ventures** — turning other activities profitable helps.
6. **History of income and losses** — a string of loss years with no revenue is
   the worst factor, and it's the one you're sitting in.
7. **Amount of any occasional profits** — none yet.
8. **Your financial status** — a taxpayer with a strong W-2 income and losses that
   conveniently shelter it draws scrutiny. This is you.
9. **Personal pleasure or recreation** — overland camping is a hobby you already
   do (`Outdoor Adventure`, `Escalade Work`). This factor cuts against you hard,
   and it's visible all over the project.

**The 3-of-5-years safe harbor** (a profit in 3 of the last 5 consecutive years
creates a presumption of profit motive) — **you cannot meet this.** You have zero
profit years.

Honest read: on today's facts, several of the nine factors point toward hobby, and
the safe harbor is unavailable. That doesn't mean it *is* a hobby — profit motive
is about genuine intent, and you can build the record that shows it — but claiming
a large equipment deduction now, before there's any revenue or businesslike
infrastructure, is claiming it into the teeth of §183.

## 2.5 Startup costs — IRC §195

- Costs incurred **before the business is "active"** are not currently deductible
  as ordinary business expenses. They're **startup costs**: up to **$5,000
  deductible in the year the active trade or business begins** (that $5,000 phases
  out dollar-for-dollar above $50,000 of startup costs), and the **remainder
  amortized over 180 months** (15 years).
- "Active" generally means you're **offering the product for sale** — not designing
  it, not building CAD, not standing up a private website.
- A computer bought now, while you're pre-launch, is more likely a **capital asset
  that doesn't begin depreciating until the business is active** (or a startup cost
  if it's a setup expense) — either way, **the benefit is deferred**, possibly for
  years, possibly forever if the business never becomes active.

## 2.6 Even if it's a real business — is the loss usable?

- **Entity type:** A sole proprietorship or single-member LLC both put the loss on
  **Schedule C**, flowing to your 1040 against W-2 income. An SMLLC gives you
  liability separation and a cleaner story but **no different tax treatment**. An
  S-corp or partnership adds cost and complexity with no benefit at this scale.
- **Passive activity rules (§469):** if you **materially participate** (you run it
  yourself — you do), it's **non-passive**, so passive-loss limits don't trap the
  loss. Good.
- **At-risk rules (§465):** you can only deduct losses up to what you've actually
  put in. Not a constraint at a $2,900 scale.
- **Excess business loss (§461(l)):** disallowed above **$256,000 (single) /
  $512,000 (MFJ)** for 2026 (OBBBA reset these down and made them permanent).
  Irrelevant at your scale — noted only for completeness.
- **Self-employment tax:** cuts the *other* way. When Bear Necessities eventually
  makes a profit, that profit owes **15.3% SE tax** on top of income tax. A real
  profit costs more than the income-tax picture suggests; a loss produces no SE
  benefit.

## 2.7 What would actually need to be true for this plan to make sense

In rough order:

1. **A genuine, documented profit motive** — separate bank account, books, a
   written plan, evidence you're pursuing profit and adjusting when things don't
   work. Not backdated. Built now, forward.
2. **An active trade or business** — the product is actually offered for sale
   (even path 1, the plans pack, counts), not just designed. This starts the
   §195 clock and moves you out of "pre-launch."
3. **Revenue, or a credible near-term path to it** — so there's profit to offset,
   §179 becomes usable, and the §183 hobby risk drops.
4. **Clean structure** — at minimum a Schedule C with real books and a dedicated
   account; an SMLLC if you want liability separation (relevant for a load-bearing
   vehicle product).
5. **A contemporaneous business-use log for the computer** — from day one.
6. **Then, and only then**, the depreciation question (bonus vs. §179 vs. MACRS vs.
   a sub-$2,500 machine under de minimis) is worth having your CPA optimize — and
   even then it saves you `deduction × ~30%`, not the sticker price.

---

## What to do, in what order — questions for your CPA

Framed as questions, because these are decisions for a professional who can see
your whole return, not for this document.

1. **On the machine itself:** "I want an always-on Mac mini (~$2,900) primarily for
   personal and hobby projects, with some use for a pre-revenue product idea. Given
   there's no business income, is there any real tax benefit to buying it 'through
   the business' this year, or should I just buy it personally and revisit if the
   business generates revenue?"
2. **On hobby vs. business:** "Bear Necessities is design-stage with zero revenue
   and overlaps a hobby I already have. If I deduct a large equipment purchase now,
   how exposed am I under §183? What specifically would you want to see in place
   before I treat this as a business on my return?"
3. **On timing:** "If I'm pre-launch, is this computer a §195 startup cost, a
   capital asset that doesn't depreciate until the business is active, or currently
   deductible? When does the depreciation clock actually start?"
4. **On structure:** "If and when I start selling — likely a small digital plans
   pack first, possibly custom builds later — do you recommend a Schedule C sole
   prop or a single-member LLC? What Philadelphia business tax obligations (BIRT,
   NPT) would that trigger?"
5. **On the de minimis election:** "If I bought a sub-$2,500 machine instead, and
   put a written capitalization policy in place at the start of next year, would
   the de minimis safe harbor let me expense it cleanly once the business is
   active? Is that simpler than depreciating a $2,900 machine?"
6. **On substantiation:** "What business-use log and records do you want me keeping
   for a home computer that's used for both the business and personal projects?"
7. **On the loss:** "If Bear Necessities runs at a loss for the first few years
   while it's genuinely a business, can those losses offset my W-2 income, and is
   there anything about my situation that would limit that?"

---

## Bottom line

- **The app** is a private brochure site for a physical product that doesn't exist
  yet. There's no software to monetize on its own.
- **The realistic near-term revenue paths** are: sell the build plans as a digital
  download (weekend of work, small niche money), and take one-off custom-build
  commissions once you've built a real prototype. Both together might produce a few
  hundred dollars over six months. Everything with real upside needs capital or an
  audience you don't have.
- **The tax plan does not hold up on today's facts.** No revenue means no profit to
  offset. A deduction is worth roughly `cost × your ~30% marginal rate` — call it
  ~$850 on a $2,900 machine — and only if the loss survives the §183 hobby-loss
  test, which on current facts it may not, and only if the timing rules (§195,
  depreciation start date) even let you take it this year, which they may not.
  **The Mac mini does not become free, or meaningfully cheap, through the
  business.** If you want it, buy it because you want it — and revisit the tax
  treatment with a CPA if and when Bear Necessities actually earns money.

## Sources

Tax rules cited above, checked September 2026 — confirm all with your CPA:

- Section 179 / bonus depreciation 2026 & OBBBA §70301 permanence: [Section179.org 2026 guide](https://www.section179.org/section_179_deduction/), [Section 179 vs Bonus Depreciation 2026](https://www.section179.org/section_179_vs_bonus_depreciation/)
- De minimis safe harbor, Reg. §1.263(a)-1(f), $2,500/item: [IRS Tangible Property Final Regulations](https://www.irs.gov/businesses/small-businesses-self-employed/tangible-property-final-regulations), [Nolo](https://www.nolo.com/legal-encyclopedia/new-irs-de-minimis-rule-deducting-business-property.html)
- Hobby loss §183, nine-factor test, 3-of-5 safe harbor: [Burr & Forman](https://www.burr.com/tax-law-insights/dont-get-tripped-up-by-hobby-loss-rules), [Meadows Collier — §183 overview](https://www.meadowscollier.com/hobby-loss-and-ranches-an-overview-of-section-183/), Treas. Reg. §1.183-2(b)
- Hobby expenses not deductible (misc. itemized deduction suspension): [Nolo — deducting hobby expenses](https://www.nolo.com/legal-encyclopedia/can-you-deduct-your-expenses-from-hobby.html), [TurboTax — IRS classifies your business as a hobby](https://turbotax.intuit.com/tax-tips/small-business-taxes/when-the-irs-classifies-your-business-as-a-hobby/L5NClTTtK) *(the "90% of hobby income" 2026 claim is from a single secondary source and is flagged as unverified)*
- Startup costs §195, $5,000 + 180-month amortization, "active trade or business": [Congressional Research Service — Section 195](https://www.congress.gov/crs_external_products/IF/HTML/IF12970.html), [26 USC 195](https://uscode.house.gov/view.xhtml?req=%28title%3A26+section%3A195+edition%3Aprelim%29)
- Computers removed from listed property (TCJA, 2018): [IRS Publication 946](https://www.irs.gov/publications/p946)
- Excess business loss §461(l) 2026 thresholds ($256k/$512k), OBBBA: [IRS Form 461 instructions](https://www.irs.gov/pub/irs-pdf/i461.pdf)
- Machine spec and price: `../Mac Mini Setup/` project files (18-core M5 Pro / 64GB, $2,899 retail / $2,679 education)
