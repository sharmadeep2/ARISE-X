---
title: Free ML to LLMOps course source verification
description: Verified public learning resources and ranked architect watch sequence across ten levels.
ms.date: 2026-09-13
status: Complete
---

## Research scope

Identify 12-18 curated free lecture/course resources for an experienced architect progressing from ML foundations to LLMOps and principal architecture. Verify official identity, scope, and discover exact YouTube links through live fetch/browser evidence. Target at least eight evidenced YouTube URLs; distinguish link verification from playback verification.

## Questions

* Which resources cover ML basics, backpropagation, PyTorch, transformers, LLM training, distributed GPUs, fine-tuning, evaluation, inference, serving, MLOps, observability, SRE, security, Kubernetes, and architecture?
* What prerequisite, watch order, exercise, cost boundary, and tooling-age caveat applies to each?
* Which links can be verified directly, and which require official-page evidence because video access is blocked?

## Findings

Sixteen resources form a selective, prerequisite-aware route. Thirteen distinct YouTube video/playlist endpoints were opened in the browser and returned matching identities. Three further Karpathy video URLs were recovered directly from his syllabus, without separate destination checks. CS229 has a verified official MP4 alternative. Some course activities require accounts, and the security course has conditional free access.

YouTube was accessible in this session. Verification means an official source link plus a matching public page title, not a guarantee that every playlist entry plays, every region has access, or every lab executes. No videos were watched end to end. No course account was created, enrollment completed, or API/GPU lab executed. Exercises below are proposed applications, not claimed official assignments unless explicitly identified.

Use the requested research date, 2026-09-13, for this report. Browser event logs displayed 2026-09-12 UTC during the session; no exact wall-clock verification timestamp is asserted.

### Verification labels

* Y: Official source and direct YouTube identity verified in the browser
* L: Exact YouTube link verified on the official source only
* M: Official course and non-YouTube media endpoint verified
* C: Public course text or course offer verified; account-gated lessons not audited
* Conditional: Current offer advertises limited-time free access, not permanent free access

### Ten-level coverage map

| Level | Learning objective | Primary resources | Required artifact or boundary |
| --- | --- | --- | --- |
| L1 | ML foundations, probability, generalization, baseline selection | R01, R03 | Baseline and held-out evaluation; refresh linear algebra as needed |
| L2 | Backpropagation, optimization, tensor reasoning, PyTorch | R02, R03, R04 | Gradient checks and reproducible training loop |
| L3 | NLP, tokenization, attention, transformers | R02, R05, R06 | Small decoder and tokenizer with shape/masking tests |
| L4 | LLM pretraining, data quality, scaling laws | R07 | Data manifest and small-model training/evaluation report |
| L5 | GPU profiling, kernels, distributed training | R07, R08 | Compute/memory/communication budget and profiler evidence |
| L6 | Fine-tuning, preference alignment, evaluation | R06, R09, R07 | Base-versus-tuned comparison on untouched domain tests |
| L7 | Inference efficiency and serving | R07, R10 | Measured latency/throughput/memory trade-off; not a complete modern serving SDK course |
| L8 | MLOps, LLMOps, observability, CI/CD | R10, R11, R12 | Versioned artifacts, evaluation gate, feedback and monitoring plan |
| L9 | Kubernetes, SRE, security | R13, R14, R15 | Local rollout, SLO/error-budget policy, authorized security assessment |
| L10 | Principal architecture and platform decisions | R16, R10, R14 | Capacity model, failure analysis, build/buy ADR and ownership model |

The mapping is a proposed curriculum, not a promise that a single video covers each named topic. Current vLLM/SGLang production configuration, GPU Kubernetes scheduling, enterprise IAM, secure software supply chains, and incident-command practice remain explicit depth gaps.

## Curated resources

### R01 Stanford CS229 Machine Learning public archive

* Creator: Stanford Engineering Everywhere, Andrew Ng. His identity is explicit in the official Lecture 1 transcript.
* Official source: <https://see.stanford.edu/Course/CS229>
* Media: No exact YouTube URL was exposed by the inspected official page. Official Lecture 1 MP4: <https://see.stanford.edu/videos/courses/see/CS229/CS229-lecture01.mp4>. The page also supplies subsequent lecture downloads and transcripts.
* Verification: M. Course fetch and browser inspection succeeded; MP4 HEAD returned HTTP 200 and `video/mp4`. Transcript fetched at <https://see.stanford.edu/materials/aimlcs229/transcripts/MachineLearning-Lecture01.html>. Playback not tested.
* Mapping and order: L1. After probability/linear-algebra refresh, start with introduction and supervised learning; continue to learning theory/generalization, then selected unsupervised learning. Reinforcement learning is optional before LLM post-training.
* Exercise: Implement a regularized regression/classification baseline in NumPy, keep train/validation/test sets separate, and explain whether errors suggest bias, variance, or data leakage.
* Cost and age: Public lectures/materials, not university credit. Historical MATLAB/Octave tooling is explicitly present in the transcript; translate exercises to Python. Do not substitute the restricted Summer 2026 website for this archive.

### R02 Neural Networks Zero to Hero including micrograd

* Creator: Andrej Karpathy
* Official source: <https://karpathy.ai/zero-to-hero.html>
* Start video: <https://youtu.be/VMj-3S1tku0>, The spelled-out intro to neural networks and backpropagation: building micrograd
* Next exact syllabus links: <https://youtu.be/PaCmpygFfXo> (building makemore), <https://www.youtube.com/watch?v=kCc8FmEb1nY> (Let's build GPT), <https://youtu.be/zduSFxRajkE> (GPT Tokenizer)
* Verification: Y for micrograd; browser returned its matching title and video-player UI. L for the three next links; all were explicitly present alongside descriptions on Karpathy's fetched syllabus.
* Mapping and order: L2-L3, bridge to L4. Python and elementary derivatives first; micrograd, makemore, the intervening MLP/activations/backprop lessons in syllabus order, GPT, then tokenizer. Do not jump straight from scalar autodiff to GPT if tensor shapes remain unclear.
* Exercise: Build scalar autodiff with finite-difference checks, reproduce it using PyTorch, then train a tiny character decoder and demonstrate why causal masking and tokenization change results.
* Cost and age: Public videos; CPU-scale exercises are feasible, larger training is not a free-compute entitlement. Backpropagation and autoregressive modeling endure; this is an instructional GPT implementation, not a current distributed trainer or production ChatGPT replica.

### R03 Practical Deep Learning for Coders 2022

* Creator: Jeremy Howard, fast.ai
* Official source: <https://course.fast.ai/>
* YouTube playlist: <https://www.youtube.com/playlist?list=PLfYUBJiXbdtSvpQjSnJJ_PmDQB_VyT5iU>
* Verification: Y. Official page explicitly calls the course free and links this playlist; browser HTTP 200 title was Practical Deep Learning for Coders.
* Mapping and order: L1-L2, early deployment preview. Coding experience is the entry requirement. Watch lessons 1 and 2 to build/deploy something useful; continue the remaining Part 1 lessons in order alongside R02 when the high-level library hides a mechanism.
* Exercise: Train a modest transfer-learning classifier, document a data split and error analysis, and compare a high-level fastai training run with a plain PyTorch loop.
* Cost and age: Videos and online book are free. Historical Kaggle/Paperspace free-resource recommendations are not a verified 2026 quota promise. fastai, Gradio, notebook setup, and deployment APIs from 2022 require version checks; the train-first pedagogy and optimization fundamentals remain useful.

### R04 Stanford CS231n Deep Learning for Computer Vision 2025

* Creator: Stanford CS231n teaching team; the current official site lists Fei-Fei Li, Ehsan Adeli, Justin Johnson and colleagues. Do not assume the current roster is identical to every 2025 lecturer.
* Official source: <https://cs231n.stanford.edu/>
* YouTube playlist: <https://www.youtube.com/playlist?list=PLoROMvodv4rOmsNzYBMe0gJY2XS8AQg16>
* Verification: Y. Source explicitly links previous-year recordings; browser HTTP 200 title identifies the linked playlist as Stanford CS231N Deep Learning for Computer Vision I 2025, not 2026.
* Mapping and order: L2, optional visual-model depth. Requires Python, calculus, linear algebra and probability. Select early classification/loss/optimization/backprop material, then neural-network training and convolutional architectures; retain playlist order within those selections.
* Exercise: Overfit a tiny image batch, diagnose a broken gradient/initialization case, then compare regularization choices on a held-out split.
* Cost and age: Public recording archive; current Canvas lectures, grading, credit and student GPU credits are not included. Durable optimization and architecture concepts; match assignments to their offering and validate framework versions rather than mixing the current syllabus with archived videos.

### R05 Stanford CS224N NLP with Deep Learning Spring 2024

* Creator: Stanford, Professor Christopher Manning for the verified 2024 playlist
* Official source: <https://web.stanford.edu/class/cs224n/>
* YouTube playlist: <https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D>
* Verification: Y. Official page labels this complete 2024 video set free; browser HTTP 200 title confirms Spring 2024 and Christopher Manning. Current Winter 2026 recordings are explicitly unavailable to non-enrolled students.
* Mapping and order: L3, conceptual support for L6. Take after R02 and basic ML. Follow word representations and neural language modeling before attention/transformers and later pretrained-model material. Select rather than repeat all fundamentals already mastered.
* Exercise: Compare embeddings, an encoder classifier and a small causal decoder on clearly different tasks; explain objective, masking and evaluation differences.
* Cost and age: Public videos/slides are distinct from paid XCS224N certificates and Stanford credit. Do not advertise the 2026 syllabus's newer lectures as part of the 2024 playlist. NLP fundamentals endure; APIs, model comparisons and frontier reasoning techniques change.

### R06 Hugging Face LLM Course

* Creator: Hugging Face course team, including Sylvain Gugger, Lewis Tunstall and other named authors
* Official source: <https://huggingface.co/learn/llm-course/chapter1/1>
* YouTube playlist: <https://youtube.com/playlist?list=PLo2EIpI_JMQvWfQndUesu0nPBAtZ9gP1o>
* Verification: Y. Source says completely free without ads and links course videos; browser HTTP 200 title was Hugging Face Course. The current written syllabus extends beyond the historical video collection; complete video parity was not checked.
* Mapping and order: L3 and L6. Python plus introductory deep learning first. Chapters 1-4 for Transformers/Hub/fine-tuning, chapters 5-8 for datasets/tokenizers/tasks, then selected advanced chapters 10-12. Use course pages to pair videos and text; skip demo-sharing chapter 9 until needed.
* Exercise: Fine-tune a small encoder on a versioned dataset and compare `Trainer` with a manual loop; retain model, tokenizer, dataset revision and evaluation outputs.
* Cost and age: Course free; Hub publishing needs an account, and GPU/hosted endpoints can cost money. The fetched FAQ currently says no certificate. Foundational explanations endure; use current Transformers/Datasets/Accelerate documentation when older recordings disagree with maintained text.

### R07 Stanford CS336 Language Modeling from Scratch Spring 2026

* Creator: Percy Liang and Tatsunori Hashimoto, Stanford
* Official source: <https://cs336.stanford.edu/>
* Exact recording link: <https://www.youtube.com/watch?v=JuoVZkPBiKk&list=PLoROMvodv4rMqXOcazWaTUHhq-yembLCV>
* Verification: Y. Official page lists this recording link and detailed schedule; browser HTTP 200 title identifies Spring 2026 Lecture 1: Overview, Tokenization. This does not establish completeness of every later recording.
* Mapping and order: L4-L7. Requires fluent Python, PyTorch, ML, memory hierarchy, calculus and probability. Follow lectures 1-4 for tokenization/accounting/architecture, 5-8 for accelerators/kernels/parallelism, 9-14 for scaling/inference/evaluation/data, then 15-17 for post-training/alignment.
* Exercise: Complete a scaled-down version of the official Basics assignment, then a Systems benchmark. Produce an explicit parameters/activations/optimizer-state memory budget and a data-cleaning comparison before considering larger training.
* Cost and age: Public lectures and assignment repositories; actual multi-GPU runs and some assignment infrastructure are not guaranteed free or externally available. Page recommends CPU correctness debugging before GPU runs and quotes dated GPU prices, not current verified rates. Pin assignment versions. Triton kernels, accelerator assumptions and parallelism APIs still need release checks.

### R08 GPU MODE profiling and collective communication selections

* Creator: GPU MODE community. The repository lists Lecture 16 speaker as Taylor Robbie and Lecture 17 speaker as Dan Johnson.
* Official source: <https://github.com/gpu-mode/lectures>, which links <https://www.youtube.com/@GPUMODE>
* YouTube selections: <https://www.youtube.com/watch?v=SKV6kDk1s94> (Lecture 16: On Hands Profiling), then <https://www.youtube.com/watch?v=T22e3fgit-A> (Lecture 17: NCCL)
* Verification: Y. Repository verifies lecture identities/topics; browser searches within the repository-linked official channel exposed both exact URLs. Separate browser visits returned HTTP 200 and matching titles. Channel search also tied Lecture 17 to its code/slides.
* Mapping and order: L5. First finish CS336 resource accounting and basic GPU/parallelism lessons; then profiling before NCCL so communication overhead has a measurable context.
* Exercise: Profile a training step, separate compute from synchronization, and compare expected versus measured scaling. Without multiple GPUs, analyze a supplied trace and derive an all-reduce communication budget; label that analysis rather than a measured benchmark.
* Cost and age: Public community lectures; hardware is separate and the recommended PMPP book is not a free resource. Enduring profiling/collective concepts; older CUDA/PyTorch profiler UI and NCCL tuning behavior are hardware/version-sensitive. Do not confuse Triton the kernel language with Triton Inference Server.

### R09 Hugging Face smol-course for fine-tuning

* Creator: Hugging Face, Ben Burtenshaw and collaborators
* Official source: <https://huggingface.co/learn/smol-course/unit0/1>
* YouTube: No exact lesson/playlist URL was exposed by the inspected onboarding page. Use its public units rather than inventing a playlist.
* Verification: C. Fetched onboarding page confirms free course, prerequisites, instruction tuning, evaluation, preference alignment, VLMs, and free certification rules. Enrolled activities and certificate issuance were not tested.
* Mapping and order: L6. Requires transformer concepts, Python and PyTorch. Unit 1 instruction tuning/chat templates, Unit 2 domain evaluation, then Unit 3 preference alignment. Delay multimodal and RL extensions until the baseline evaluation is stable.
* Exercise: Compare a small base model and supervised fine-tune on a fixed domain suite; test chat-template correctness, held-out contamination, regressions and memory consumption. Add a parameter-efficient variant using maintained PEFT guidance.
* Cost and age: Free account/course and advertised free certificates; suggested Hugging Face Pro and GPU access are optional paid resources. The fetched syllabus marks some later units as future October/November releases without a reliable year context; do not promise those units are complete. TRL/PEFT signatures and supported quantization combinations evolve quickly.

### R10 Full Stack Deep Learning 2022

* Creator: Full Stack Deep Learning teaching team; selected deployment lecture by Josh Tobin
* Official course: <https://fullstackdeeplearning.com/course/2022/>
* Verified lecture page: <https://fullstackdeeplearning.com/course/2022/lecture-5-deployment/>
* YouTube: <https://www.youtube.com/watch?v=W3hKjXg7fXM>
* Verification: Y. Course says all lecture/lab material is free. HTTP 200 lecture HTML contains `https://www.youtube-nocookie.com/embed/W3hKjXg7fXM?list=PL1T8fO7ArWleMMI8KPJ_5D5XSlovTW_Ur`. The watch URL was mechanically formed from that observed ID and independently verified as Lecture 05: Deployment (FSDL 2022), HTTP 200.
* Mapping and order: L7-L8 and L10. After a trained model, watch Lecture 1 on when to use ML, 2 on infrastructure, 3 on testing, 4 on data, 5 on deployment, 6 on continual learning; revisit 8 on teams and 9 on ethics at the architecture stage. Only Lecture 5's individual video endpoint was tested here.
* Exercise: Separate model and UI lifecycles, compare batch versus request-time serving, specify gradual rollout/rollback, then add feedback capture and tests.
* Cost and age: Public lectures, not free hosted labs by implication. W&B accounts, cloud deployment, API calls and GPU serving have separate conditions. Batch/service separation and feedback loops endure; 2022 statements favoring CPU/serverless are not universal advice for modern autoregressive LLMs. Serving frameworks and vendors may have changed substantially.

### R11 Full Stack Deep Learning LLM Bootcamp Spring 2023

* Creator: Full Stack Deep Learning; selected LLMOps lecture by Josh Tobin
* Official course: <https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/>
* Lecture page: <https://fullstackdeeplearning.com/llm-bootcamp/spring-2023/llmops/>
* YouTube: <https://www.youtube.com/watch?v=Fquj2u7ay40>
* Verification: Y. Public course states free access. HTTP 200 lecture HTML contains `https://www.youtube-nocookie.com/embed/Fquj2u7ay40?list=PL1T8fO7ArWleyIqOy37OVXsP4hFXymdOZ`; derived watch URL independently returned HTTP 200 with title LLMOps (LLM Bootcamp).
* Mapping and order: L7-L8 and L10. After R06, select Foundations as recap, Prompt Engineering, Augmented Language Models, then LLMOps and askFSDL walkthrough. Only LLMOps's individual video endpoint was checked; the course page verifies other lecture identities and scopes.
* Exercise: Create a small retrieval application evaluation set, version prompts/retrieval/model choices, compare errors by category, and specify a deployment gate informed by user feedback.
* Cost and age: Free recordings; historical sponsor credits do not promise free API, vector database or GPU usage now. Licensing, task-based evaluation, prompt versioning and feedback principles remain useful. GPT-4/Claude rankings, model availability and 2023 LangChain/hosting examples are historical, not a 2026 selection guide.

### R12 DataTalksClub MLOps Zoomcamp

* Creator: DataTalks.Club; Cristian Martinez, Alexey Grigorev and Emeli Dral are listed instructors
* Official source: <https://github.com/DataTalksClub/mlops-zoomcamp>
* YouTube playlist: <https://www.youtube.com/playlist?list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK>
* Verification: Y. Public repository describes the free course and exact playlist; browser HTTP 200 title MLOps Zoomcamp, with description linking back to the repository.
* Mapping and order: L8, monitoring bridge to L9. Requires Python, Docker, CLI and ML familiarity. Modules 1-2 for maturity/tracking, 3 orchestration, 4 deployment, 5 monitoring, 6 testing/CI/IaC, then project. Focus on monitoring and release discipline if experiment tracking is already familiar.
* Exercise: Track model/data revisions, register a candidate, test and deploy locally, then build Prometheus/Grafana operational metrics and an Evidently data-quality/drift report. Keep drift alerts distinct from proven quality degradation.
* Cost and age: Free self-paced materials. Current repository says no 2026 live cohort and no self-paced certificate; live-cohort certificates are not an enrollment promise. Cloud exercises can incur charges. MLflow, Prefect and Evidently APIs vary by cohort; select coherent materials instead of combining refreshed repository pages and old videos blindly.

### R13 Introduction to Kubernetes LFS158

* Creator: The Linux Foundation
* Official source: <https://training.linuxfoundation.org/training/introduction-to-kubernetes/>
* Course portal: <https://trainingportal.linuxfoundation.org/learn/course/introduction-to-kubernetes>
* YouTube: No exact course video/playlist URL discovered. The public source describes course material and video demonstrations; access is through the portal.
* Verification: C. Fetched public offer confirms Kubernetes architecture, Minikube, building blocks, authn/authz/admission, services, volumes, ConfigMaps/Secrets and Ingress. It displays $0, login before enrollment, a digital badge, and 90 days of access. Portal enrollment and lessons were not tested.
* Mapping and order: L9. Linux/container familiarity helps. Chapters 2-5 for architecture, 6-9 for cluster/building blocks, 10-15 for access control, networking, deployment and configuration. Experienced Kubernetes operators can use a gap check instead of watching everything.
* Exercise: Run a small CPU model service locally, separate configuration from credentials, perform a rollout and rollback, and document access boundaries. GPU scheduling and multi-tenant model isolation require further material.
* Cost and age: Advertised course is $0 with a badge, not CKA/CKAD certification. Local labs avoid cloud fees; hardware still matters. Do not repeat obsolete claims that this exact offer requires a paid edX certificate. Reconcile manifests and controller installation with the selected Kubernetes release.

### R14 Google The Art of SLOs

* Creator: Google Customer Reliability Engineering; companion explainer features Riccardo Carlesso
* Official source: <https://sre.google/resources/practices-and-processes/art-of-slos/>
* YouTube: <https://www.youtube.com/watch?v=E3ReKuJ8ewA>
* Verification: Y. Public page supplies workshop slides, participant/facilitator handbooks, SLO worksheets and CC-BY-4.0 terms. HTTP 200 HTML exposes the companion video link; browser HTTP 200 title matches The Art of SLOs (Service Level Objectives).
* Mapping and order: L9-L10. After service deployment/monitoring, watch the explainer, study workshop slides, complete participant exercises, then compare facilitator answers. This video is an introduction, not a recording of the entire workshop.
* Exercise: Define separate availability, time-to-first-token, completion-latency and task-quality indicators; specify valid-event denominators, target windows, error budgets and escalation ownership. Do not collapse all quality and reliability into one number.
* Cost and age: Public video and reusable workshop materials. The separately linked Coursera course/certificate is not included or verified free. User-centered SLIs and error budgets endure; calibrate targets to present workload economics, not borrowed sample percentages.

### R15 Red Teaming LLM Applications conditional free option

* Creator: DeepLearning.AI with Giskard; Matteo Dora and Luca Martial
* Official source: <https://www.deeplearning.ai/short-courses/red-teaming-llm-applications/>
* Official introductory lesson: <https://learn.deeplearning.ai/courses/red-teaming-llm-applications/lesson/t1tp1/introduction>
* YouTube: No exact full-course video/playlist link discovered. Do not substitute a promotional trailer for the actual course.
* Verification: C, Conditional. Public fetched page lists seven video lessons and five code examples, names instructors, and advertises free access only for a limited beta period. Graded assignment/accomplishments are marked Pro. Lesson enrollment/playback was not tested, so this is not an unconditional free-course guarantee.
* Mapping and order: L9. Basic Python plus R11's application/evaluation context. Follow vulnerability overview, manual red teaming, scaling, LLM-assisted tests, then full assessment. Use only your own system or an authorized sandbox.
* Exercise: Define an authorized test scope, evaluate an intentionally isolated application for instruction/data-boundary failures, record findings and mitigations, and add safe regression cases. Do not test third-party production services without permission.
* Cost and age: Free access is explicitly conditional; account, API use and Pro achievements are separate. Recheck before assigning. Security testing principles endure, but Giskard integrations and attack/defense coverage evolve; this is not a comprehensive IAM, supply-chain, privacy or Kubernetes security course.

### R16 Google SRE Classroom Distributed ImageServer

* Creator: Google's Site Reliability Engineering group
* Official source: <https://sre.google/classroom/imageserver/>
* Official recording short link: <https://goo.gle/imageserver-video>
* Discovered YouTube destination: <https://m.youtube.com/watch?v=bOXkgMuVuYY>. Browser canonical destination: <https://www.youtube.com/watch?app=desktop&v=bOXkgMuVuYY>
* Verification: Y. Public page explicitly provides slides and a prerecorded workshop video. HEAD followed the official short link to the mobile YouTube URL, HTTP 200; browser resolved the canonical URL, HTTP 200, title SRE Classroom: Design a Distributed System in One Hour. The title difference is expected and source linkage establishes identity.
* Mapping and order: L10. After R14 and distributed-systems basics, read requirements, propose an initial design, watch the worked solution, and compare against the NALSD workbook. Use the lecture title as identity, not a promise that an architect masters the topic in an hour.
* Exercise: Adapt its capacity/failure reasoning to a model-serving platform: size replicas, memory, request queues and redundancy; identify failure domains and backpressure; defend managed versus self-hosted trade-offs in an ADR. Revisit FSDL teams/project-management material for ownership.
* Cost and age: Public CC-BY-4.0 workshop materials/video. The optional implementation uses cloud services and Kubernetes and is not automatically free. Back-of-the-envelope design and SLO reasoning endure; replace historical latency/reference numbers with measured hardware and workload data. The original exercise is an image service, not an LLM inference course.

## Ranked watch sequence

Ranks are a recommended execution order, not a requirement to watch sixteen complete courses. Exit a stage by demonstrating its artifact; experienced architects should skip familiar general software architecture introductions but not ML evaluation or resource accounting.

| Rank | Resource and selected route | Completion evidence |
| --- | --- | --- |
| 1 | R01 supervised learning and generalization selections | Explain a baseline, loss, split strategy and failure analysis |
| 2 | R02 micrograd through makemore fundamentals | Hand-derived gradient agrees with numerical and autodiff checks |
| 3 | R03 fast.ai lessons 1-2, then targeted Part 1 gaps | Train and expose a small useful model |
| 4 | R04 optimization/training selections, optional CV depth | Diagnose gradient and overfitting problems |
| 5 | R02 GPT/tokenizer, then R05 language-model/transformer selections | Explain tokens, attention, masking and training objective |
| 6 | R06 chapters 1-8, selected advanced units later | Reproducible model/tokenizer/data/evaluation artifacts |
| 7 | R07 lectures 1-8 and small Basics/Systems exercises | Measured compute/memory budget and working small decoder |
| 8 | R08 profiling, then NCCL | Distinguish compute, memory and communication bottlenecks |
| 9 | R07 scaling/data/evaluation/post-training; R09 units 1-3 | Base-versus-tuned evaluation with documented contamination controls |
| 10 | R07 inference, then R10 testing/data/deployment selections | Serving capacity benchmark and rollback design |
| 11 | R11 augmented models and LLMOps | Application-specific tests and prompt/retrieval versioning |
| 12 | R12 tracking through monitoring/CI/project selections | Operational monitoring, data monitoring and release gate |
| 13 | R13 Kubernetes architecture/access/deployment gaps | Local deployment and controlled rollout/rollback |
| 14 | R14 video plus SLO workshop | SLI definitions, error-budget policy and stakeholder agreement |
| 15 | R15 security lessons, only after confirming free access | Authorized assessment and safe regression suite |
| 16 | R16 NALSD workshop plus R10 teams/ethics revisit | Principal-level ADR with capacity, risks, costs and ownership |

## Source evidence log

### Publisher verification ledger

All sources below were actually fetched or visited in this session. Resource sections above give exact publisher/media URLs and the evidence-specific scope. No search-result snippet alone was accepted as proof.

| Evidence | Resource | Method and observation |
| --- | --- | --- |
| E01 | R01 | Official course fetched and browser anchors inspected; transcript names Andrew Ng; MP4 HEAD 200 with video/mp4 |
| E02 | R02 | Official syllabus fetched; exact video anchors and lesson descriptions recovered; micrograd browser title/player confirmed |
| E03 | R03 | Official landing page fetched, free status and 2022 scope explicit; linked playlist browser 200 |
| E04 | R04 | Official 2026 page directs outsiders to prior recordings; linked playlist browser title identifies 2025 |
| E05 | R05 | Official page explicitly separates restricted 2026 recordings, free 2024 playlist and paid enrollment options |
| E06 | R06 | Official introduction fetched; free status, prerequisites, chapter map and playlist link recovered |
| E07 | R07 | Official 2026 schedule fetched; linked recording browser 200; 2025 archive also fetched, not misrepresented as latest |
| E08 | R08 | Official GitHub lecture list fetched; linked channel searched in browser for Profiling and NCCL; exact anchors recovered and visited |
| E09 | R09 | Public onboarding fetched; free course/certification terms, prerequisites and incomplete later-unit schedule observed |
| E10 | R10 | Course and Deployment page fetched; raw HTML 200 exposed privacy-enhanced embed; equivalent watch URL identity independently checked |
| E11 | R11 | Bootcamp and LLMOps page fetched; raw HTML 200 exposed privacy-enhanced embed; equivalent watch URL identity independently checked |
| E12 | R12 | Public owner repository fetched; exact playlist and self-paced/no-certificate terms observed; playlist browser 200 |
| E13 | R13 | Official public offer fetched; $0, login, 90-day access, badge and chapter list observed; no enrollment test |
| E14 | R14 | Official workshop fetched; raw HTML 200 supplied exact companion YouTube URL; browser title confirmed |
| E15 | R15 | Official public course page fetched; limited-time beta free offer and Pro gating observed; no lesson-access test |
| E16 | R16 | Official workshop fetched; official short-link HEAD 200 resolved to YouTube; browser canonical page title confirmed |

### Direct YouTube identity checks

All thirteen rows are distinct endpoints actually opened, not generated playlist guesses. Playlist verification covers the landing-page identity, not every contained video. Except micrograd's initial open, the browser explicitly returned HTTP 200. Micrograd returned a matching title and player UI; its HTTP status was not separately recorded.

| Resource | Exact endpoint checked | Observed identifying title |
| --- | --- | --- |
| R02 | <https://www.youtube.com/watch?v=VMj-3S1tku0> | The spelled-out intro to neural networks and backpropagation: building micrograd |
| R03 | <https://www.youtube.com/playlist?list=PLfYUBJiXbdtSvpQjSnJJ_PmDQB_VyT5iU> | Practical Deep Learning for Coders |
| R04 | <https://www.youtube.com/playlist?list=PLoROMvodv4rOmsNzYBMe0gJY2XS8AQg16> | Stanford CS231N Deep Learning for Computer Vision I 2025 |
| R05 | <https://www.youtube.com/playlist?list=PLoROMvodv4rOaMFbaqxPDoLWjDaRAdP9D> | Stanford CS224N Natural Language Processing with Deep Learning I Spring 2024 I Professor Christopher Manning |
| R06 | <https://youtube.com/playlist?list=PLo2EIpI_JMQvWfQndUesu0nPBAtZ9gP1o> | Hugging Face Course |
| R07 | <https://www.youtube.com/watch?v=JuoVZkPBiKk&list=PLoROMvodv4rMqXOcazWaTUHhq-yembLCV> | Stanford CS336 Language Modeling from Scratch, Spring 2026, Lecture 1: Overview, Tokenization |
| R08 | <https://www.youtube.com/watch?v=SKV6kDk1s94> | Lecture 16: On Hands Profiling |
| R08 | <https://www.youtube.com/watch?v=T22e3fgit-A> | Lecture 17: NCCL |
| R10 | <https://www.youtube.com/watch?v=W3hKjXg7fXM> | Lecture 05: Deployment (FSDL 2022) |
| R11 | <https://www.youtube.com/watch?v=Fquj2u7ay40> | LLMOps (LLM Bootcamp) |
| R12 | <https://www.youtube.com/playlist?list=PL3MmuxUbc_hIUISrluw_A7wDSmfOhErJK> | MLOps Zoomcamp |
| R14 | <https://www.youtube.com/watch?v=E3ReKuJ8ewA> | The Art of SLOs (Service Level Objectives) |
| R16 | <https://www.youtube.com/watch?app=desktop&v=bOXkgMuVuYY> | SRE Classroom: Design a Distributed System in One Hour |

The CS336 title's visual separators are normalized to commas in this table; its endpoint and identity are unchanged. No timestamps, lesson runtimes, complete-playback claims or invented video IDs are supplied.

### Redirects and excluded access paths

* <https://stanford-cs336.github.io/spring2025/> returned a redirect notice to the Stanford archive. Successfully fetched <https://cs336.stanford.edu/spring2025/> and the latest <https://cs336.stanford.edu/> instead.
* <https://cs229.stanford.edu/> currently exposes Summer 2026 information with restricted resources. The fetched <https://cs229.stanford.edu/syllabus-autumn2018.html> did not provide a public YouTube link. R01 uses the verified SEE archive instead; no 2018 playlist ID was guessed.
* The candidate CS229 links.html path returned HTTP 404 and is excluded from recommendations. No failed endpoint is used as a learner start link.
* FSDL text extraction omitted the player iframe. Raw publisher HTML recovered the exact IDs; independent YouTube page visits confirmed them rather than treating a generic channel link as a course playlist.
* The fetched Google SRE Classroom overview, <https://sre.google/classroom/>, established workshop scope. A separate SRE Fundamentals landing page was inspected but not added, keeping the list bounded and avoiding unverified enrollment terms.
* GPU MODE Lecture 44 and Lecture 67 appeared in official-channel searches but were not added to the learner sequence. The narrower profiling/NCCL pair supplies the required systems bridge without an uncurated channel dump.

## Limitations and remaining research

The requested source verification and curated sequence are complete. These follow-ups concern deeper implementation readiness, not unresolved resource identity:

* [ ] Recheck R15's limited-time free access before assigning it; find a permanently public replacement if the offer ends.
* [ ] Confirm account-gated R13/R15 lesson access and R09 certificate eligibility from the learner's account, if certification matters.
* [ ] Verify a current vLLM or SGLang serving lab and GPU Kubernetes scheduling/tenant-isolation material against chosen releases.
* [ ] Add deeper enterprise identity, model/data supply-chain security and incident-response practice if required for the final platform role.
* [ ] Match video editions to pinned assignment repositories and test labs in a disposable environment before publishing an executable syllabus.
* [ ] Measure available GPU memory and establish a spend ceiling before distributed-training exercises; none of the free-video claims includes unlimited compute.

No clarifying question blocks this research. Before turning it into a scheduled course, ask whether the learner has GPU access, wants certificates, and primarily targets training infrastructure, application LLMOps, or inference-platform architecture. Those choices change exercise depth, not the verified source identities.