# Design System & Copywriting Guidelines: "The Transparent Blackbox"

This document serves as the absolute source of truth for the UI development of the **AI-Driven Requirements Delivery Flow Engine**. It synthesizes Vercel's high-density utility, Apple's tactile glassmorphism, and AI-native micro-interactions under Dieter Rams' philosophy of *"Less, but better."*

---

## 1. Color Palette (Tailwind Utility Classes)

We rely on a minimalist grayscale foundation to reduce visual noise, punctuated by deliberate "Geeky" AI accents only when the system is actively working or requires attention.

*   **Backgrounds (The Canvas)**
    *   Main Console: `bg-zinc-50`
    *   AI Terminal/Code Spaces: `bg-zinc-950`
*   **Surfaces (The Elements)**
    *   Standard Console Panels: `bg-white`
    *   Widget/Modals (Apple Glassmorphism): `bg-white/70` or `bg-white/80`
*   **Borders (Structural Definition)**
    *   Subtle Dividers: `border-zinc-200`
    *   Dark Mode/Terminal Borders: `border-zinc-800`
    *   Glassmorphism Edges: `border-white/20`
*   **Text Hierarchy (Clarity through Contrast, not Size)**
    *   Primary (Headers, Active Data): `text-zinc-900`
    *   Secondary (Descriptions, Metadata): `text-zinc-500`
    *   Tertiary/Disabled: `text-zinc-400`
*   **Primary Accents (The "Geeky" AI Glow)**
    *   Text/Icons: `text-purple-500`
    *   Subtle Backgrounds: `bg-purple-500/10`
    *   Glow Effects: `shadow-[0_0_15px_rgba(168,85,247,0.15)]`
    *   Focus States: `focus-visible:ring-2 focus-visible:ring-purple-500/50`

---

## 2. Typography & Spacing

Hierarchy is established through **font-weight and color contrast**, rarely through font-size. Avoid huge headers; let the whitespace do the heavy lifting.

*   **Grid System (4pt/8pt)**: Strictly enforce spacing with Tailwind utilities like `gap-2`, `gap-4`, `p-4`, and `p-6`.
    *   *Tight grouping (related items):* `gap-2`
    *   *Loose grouping (distinct sections):* `gap-6` or `gap-8`
*   **Font Weights**:
    *   `font-medium`: For primary labels, buttons, and section titles.
    *   `font-normal`: For all body text and secondary descriptions.
*   **Font Families**:
    *   Standard UI: Default sans-serif (`font-sans`).
    *   AI Outputs/Logs: Strict monospace (`font-mono`) to evoke the "engine" feel.
*   **Sizing constraints**: Default to `text-sm` for most UI elements. Use `text-xs` for microcopy. Only use `text-lg` or `text-xl` for the absolute top-level Hero/Page titles.

---

## 3. Component Aesthetics ("Dieter Rams" Filter)

Strip away the non-essential. No heavy shadows, no unnecessary background colors. Every interactive element must have a transition.

### A. The Standard Console Card (Feishu/Vercel Style)
High-density, professional, and entirely unobtrusive.
```html
<!-- Actionable Tailwind -->
<div class="bg-white border border-zinc-200 shadow-sm rounded-lg p-6 transition-shadow hover:shadow-md">
  <!-- Content -->
</div>
```

### B. The Injected AI Widget & Approval Modals (Apple Style)
Premium, tactile, and spatially elevated above the host site. Uses heavy blur and soft, deep shadows.
```html
<!-- Actionable Tailwind -->
<div class="backdrop-blur-xl bg-white/70 shadow-2xl rounded-2xl border border-white/20 ring-1 ring-zinc-900/5 p-6">
  <!-- Content -->
</div>
```

### C. The AI `RUNNING` State (Geeky Micro-interaction)
Represents the "Transparent Blackbox." Users should feel the engine working without being overwhelmed.
```html
<!-- Actionable Tailwind -->
<div class="bg-zinc-950 text-zinc-300 font-mono text-xs rounded-md border border-zinc-800 p-4 shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)] relative overflow-hidden">
  <!-- Subtle Purple Glow indicating AI activity -->
  <div class="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-purple-500/50 to-transparent animate-pulse"></div>
  <p class="text-purple-400">> Synthesizing requirements...</p>
</div>
```

### D. Interactive States (Mandatory)
Every button or link must react predictably.
*   **Primary Button**: `bg-zinc-900 text-white font-medium rounded-md px-4 py-2 hover:bg-zinc-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/50`

---

## 4. UX Copywriting Dictionary

**Core Rule**: Clear > Clever. Start with the Action. Positive Phrasing.

### Empty States
Don't just declare a void; offer the immediate next step.
*   🔴 **Before**: *There are no pipelines configured yet in the system.*
*   🟢 **After**: *No pipelines yet. Create your first pipeline to start processing requirements.*
*   *Rationale*: Tells the user exactly what to do next to populate the state, shifting from a dead-end to an invitation.

### AI Loading / Thinking States
Make it sound like an industrial engine processing data, not a generic web spinner.
*   🔴 **Before**: *AI is thinking... / Loading...*
*   🟢 **After**: *Synthesizing delivery flow... / Analyzing requirements...*
*   *Rationale*: Replaces generic waiting with specific, active verbs that build trust in the "engine's" capability.

### Approval Modals (Human-in-the-Loop)
Buttons must describe exactly what happens when clicked using the `[Verb] + [Noun]` pattern.
*   🔴 **Before**: *Submit / Cancel / Yes / No*
*   🟢 **After**: *Approve flow / Reject & edit*
*   *Rationale*: Removes all ambiguity. The user knows exactly what state the system will enter upon clicking.

### Error States
Never blame the user. Explain the failure and the immediate fix.
*   🔴 **Before**: *HMR Error 500: Failed to generate preview because you wrote invalid syntax.*
*   🟢 **After**: *Preview failed to load. Check the component syntax and try again.*
*   *Rationale*: Focuses on the objective failure and the actionable solution without using aggressive or technical jargon.