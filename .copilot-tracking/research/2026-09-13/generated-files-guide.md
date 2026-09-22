<!-- markdownlint-disable-file -->
---
title: Understanding the Generated Files
description: Guide to the learning handbook, video references, publication tools, and validation artifacts
ms.date: 2026-09-13
ms.topic: reference
---

## Task Researcher: Understanding the Generated Files

You only need three files for learning. Most other files were created while
formatting and checking the PDF. They are not additional lessons or things you
need to study.

This guide documents the explanation provided in the conversation. The folder
contains both learner-facing documents and publication/browser-validation
artifacts, which explains the large number of files.

Publication folder: .copilot-tracking/research/2026-09-13/

All local paths below are workspace-relative to C:/Users/sharmadeep/ARISE-X.
Recorded sizes and counts describe the earlier inventory, before this guide was
added; they are not a continuously updated directory count.

## 1. The three files that matter

| Format   | What it contains                                                        | How to use it                                                                                   |
|----------|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| PDF      | The 68-page learning plan, Module 1, exercises, architecture, references | Start here. Best for reading, printing, and sharing. Works independently of companion assets.     |
| Markdown | The authoritative, editable source of the handbook                      | Open in VS Code to search, annotate, or copy lab code. This is the consolidated learning document. |
| HTML     | A browser-readable edition with linked contents and rendered equations  | Use for browser reading. Requires local assets; copying this file alone is not fully portable.    |

Files:

* PDF: .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan.pdf
* Markdown: .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md
* HTML: .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan.html

These are three formats of the same handbook, not three separate courses.
Despite "research" in the Markdown filename, it is the consolidated learning
handbook rather than another preliminary report.

The PDF and HTML are generated snapshots. Editing the Markdown does not
automatically update them.

## 2. Where are the YouTube training references?

They are inside the main handbook, not in a separate video folder. Videos were
not downloaded.

### Open these sections

In .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md:

* Sixteen-resource course catalogue, lines 2401-2596: Course names, creators,
  video/course links, prerequisites, recommended selections, and access caveats.
* Ranked watch sequence, lines 2597-2620: Recommended order and the learning
  evidence you should produce after studying each resource.
* Karpathy micrograd and subsequent videos, lines 2446-2456: The most relevant
  starting reference for Module 1.

Line ranges refer to the published handbook version inspected for the inventory.
If the document changes, search by section title instead.

In the PDF, use Ctrl+F and search for `Sixteen-resource`, `Ranked watch sequence`,
`micrograd`, or `MLOps Zoomcamp`.

### Examples of included resources

| Topic                       | Resource                                                                                                               |
|-----------------------------|------------------------------------------------------------------------------------------------------------------------|
| Training and backpropagation | [Karpathy: building micrograd](https://www.youtube.com/watch?v=VMj-3S1tku0)                                                |
| Practical deep learning     | [fast.ai playlist](https://www.youtube.com/playlist?list=PLfYUBJiXbdtSvpQjSnJJ_PmDQB_VyT5iU)                              |
| NLP and transformers        | [Stanford CS224N playlist](https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D)                        |
| Hugging Face workflows      | [Hugging Face course playlist](https://youtube.com/playlist?list=PLo2EIpI_JMQvWfQndUesu0nPBAtZ9gP1o)                       |
| LLMOps                      | [Full Stack Deep Learning: LLMOps](https://www.youtube.com/watch?v=Fquj2u7ay40)                                            |
| MLOps lifecycle             | [MLOps Zoomcamp playlist](https://www.youtube.com/playlist?list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK)                         |

Sixteen resources does not mean sixteen YouTube courses. Some resources use
official lecture downloads, written lessons, or enrollment portals. Free learning
material does not imply free GPUs or hosted services. Access and playback can
change; consult the catalogue's verification and access caveats.

The SRE Classroom video shared during this conversation belongs to the later
architecture stage. It is not the recommended starting point for Module 1:
[SRE Classroom: Design a Distributed System in One Hour](https://www.youtube.com/watch?app=desktop&v=bOXkgMuVuYY).

## 3. What are the other files and folders?

They support document production, not model training.

| File or group                      | Purpose                                                                                      | Needed for studying?                                        |
|------------------------------------|----------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| Python renderer                    | Converts Markdown into a formatted publication                                                | No; needed for rebuilding the handbook                      |
| Browser rendering helper           | Uses Chromium to produce the PDF and inspect layout                                           | No; this is not an ML training script                       |
| Print stylesheet                   | Controls fonts, margins, tables, code formatting, and pagination                               | No; retain for rebuilding                                   |
| Rendering-assets folder            | Local KaTeX math assets, fonts, PDF.js inspection assets, licenses, and integrity records       | Not directly; supports browser rendering and regeneration   |
| Layout-test document and outputs   | Synthetic tests for equations, long code, tables, and links                                    | No; this is not another lesson                              |
| Validation folders                 | Layout reports, PDF text checks, screenshots, logs, and browser working directories            | No; these are evidence and working artifacts                |
| Supporting subagent reports        | Research notes used to assemble and check the handbook                                        | Optional; useful for provenance and validation details      |

### Publication tools and assets

* Python renderer: .copilot-tracking/research/2026-09-13/render_learning_handbook.py
* Browser helper: .copilot-tracking/research/2026-09-13/render_browser.mjs
* Stylesheet: .copilot-tracking/research/2026-09-13/handbook-print.css
* Asset bundle: .copilot-tracking/research/2026-09-13/render-assets/

### Layout fixtures and validation

* Fixture source: .copilot-tracking/research/2026-09-13/render-fixture.md
* Fixture PDF: .copilot-tracking/research/2026-09-13/render-fixture.pdf
* Fixture HTML: .copilot-tracking/research/2026-09-13/render-fixture.html
* Fixture validation: .copilot-tracking/research/2026-09-13/render-fixture.validation/
* Handbook validation: .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan.validation/

The supporting research notes are in a separate sibling hierarchy:
.copilot-tracking/research/subagents/2026-09-13/.

### Why are there so many files?

The earlier dated-folder inventory found approximately:

* 15,875 files.
* 854.6 MiB total.
* 842.9 MiB, about 98.6%, inside 88 isolated browser-run directories.

Those browser directories contain profiles, caches, and other working files
created during PDF rendering and inspection. They are not training datasets,
downloaded models, or extra course content. Working artifacts and learner-facing
documents were not separated clearly enough in the original publication layout.

## 4. How should you use the material?

### Step 1: Read the roadmap

Open the PDF and review the ten-level journey, study-hour estimates, and the
first-two-week schedule. Treat the schedule as adjustable rather than a requirement
to finish everything quickly.

Schedule source:
.copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md,
lines 170-193.

### Step 2: Study only Module 1 initially

Module 1 source:
.copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md,
lines 194-1061.

Work through:

1. The training lifecycle.
2. Forward pass and loss.
3. Hand-derived gradients.
4. The optimizer update.
5. Failure modes and checkpoint state.

Do not try to study all later architecture briefings immediately. The handbook
contains a complete learning plan and a deep first lesson; later lessons expand
progressively.

### Step 3: Use the matching video

Watch the relevant portions of micrograd, then return to the numerical example.
The goal is to explain the computation yourself, not merely finish the video.

### Step 4: Attempt the lab

Lab source:
.copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md,
lines 658-1016. Setup and code are at lines 674-958.

Copy code from Markdown rather than the PDF to avoid print-induced wrapping.
The program is embedded in the handbook; the renderer scripts are not the lab.
The lab still needs execution in a separate PyTorch learning environment. Its
runtime has not yet been validated. Syntax and worked arithmetic checks do not
establish runtime correctness.

### Step 5: Answer questions in the conversation

Submit your derivation, lab observations, or interview answers in the conversation
for critique and expansion of the next lesson. The handbook is a learning plan
and reference, not an automated learning platform or progress tracker.

## 5. What should you keep or ignore?

| Goal                                  | What to keep                                                                 |
|---------------------------------------|------------------------------------------------------------------------------|
| Reading and sharing                   | PDF                                                                          |
| Continued learning and future edits   | PDF and authoritative Markdown                                               |
| Browser reading                       | HTML and its required local KaTeX stylesheet/fonts at their referenced paths   |
| Rebuilding the publication            | Markdown, renderer scripts, stylesheet, and complete rendering asset bundle    |
| Retaining verification evidence       | Final validation reports and relevant screenshots                             |

For now, ignore fixture outputs, validation screenshots, logs, browser profiles,
and supporting research notes unless you need their technical details.

The PDF needs no companion assets. The existing HTML references local KaTeX assets
at an absolute location, so copying HTML alone is not portable. Regeneration also
requires a compatible Python environment with MarkdownIt, Node, and Chromium.
This guide does not execute regeneration or change any application dependencies.

The browser working directories are potential cleanup candidates after checking
that they are no longer in use. Validation reports and screenshots are audit
evidence rather than mere cache. Do not remove the source, assets, or rendering
tools if you want to retain the existing rebuild workflow.

Nothing was deleted or moved as part of documenting this guide.

## Summary and detailed evidence

| Need                    | Where to go                                                                                                      |
|-------------------------|------------------------------------------------------------------------------------------------------------------|
| Start reading           | .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan.pdf                                            |
| Copy code or edit notes | .copilot-tracking/research/2026-09-13/ml-llm-lifecycle-learning-plan-research.md                                     |
| Find training videos    | Course catalogue and ranked watch sequence in the handbook                                                       |
| Next learning action    | Read Module 1, watch micrograd selectively, then attempt the numerical exercise                                   |
| Detailed inventory      | .copilot-tracking/research/subagents/2026-09-13/final-handbook-publication-research.md, section starting at line 259 |

The detailed inventory records the files, dependency distinctions, and original
validation evidence. This guide explains how to use those outputs; it does not
replace or modify the learning handbook, PDF, or HTML.