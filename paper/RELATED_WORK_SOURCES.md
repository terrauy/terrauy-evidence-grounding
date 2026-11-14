# Related-work and licensing sources (verified 2026-11-13)

Every external claim in the technical report was checked against the source below. **Claims not verified are not used.**

## EO language models and context

| Claim | Source |
|---|---|
| EVE (Earth Virtual Expert), an ESA AI platform for EO questions, built with ESA Φ-lab and partners | https://www.esa.int/Applications/Observing_the_Earth/FutureEO/Introducing_ESA_s_Earth_Virtual_Expert |
| EVE paper: Atrio et al., *EVE: A Domain-Specific LLM Framework for Earth Intelligence*, ACL 2026 Industry Track | https://aclanthology.org/2026.acl-industry.72/ · https://arxiv.org/abs/2604.13071 |
| EVE-Instruct is a 24B model built on Mistral Small 3.2 | arXiv 2604.13071; model card https://huggingface.co/eve-esa/EVE-Instruct |
| EVE-Instruct license: Apache-2.0 | https://huggingface.co/eve-esa/EVE-Instruct |
| The model card's code example uses its own system prompt; the card does not call it "recommended" | https://huggingface.co/eve-esa/EVE-Instruct |
| Observed discrepancies in the card (reported as facts, not used in claims): the `base_model` metadata names Mistral-Small-3.1-24B-Instruct-2506, which is not a public repository, while the text and the paper say 3.2; the card's BibTeX points to an unrelated arXiv id | model card and HF API |
| ESA Φ-lab and BIFOLD Agentic AI for EO workshop, Berlin, 19–21 Oct 2026; takeaways call for "community benchmarks to assess whether agents are trustworthy" | https://philab.esa.int/five-takeaways-from-the-agentic-ai-for-earth-observation-workshop/ |
| Φ-lab visiting-researcher call on agentic AI for EO, which lists benchmarks and evaluation protocols as an objective | https://cin.philab.esa.int/schemes/opportunity-for-visiting-researchers-in-agentic-ai-systems-for-earth-observation |
| EOVC (EO Virtual Constellation): an ESA Φ-lab-funded concept to federate space and ground assets, developed by CS Group | https://eovc.cs-soprasteria.com/ · https://www.cs-soprasteria.com/en/?p=80754 |
| "ESA-EO-Bench" | **Not found. Not used.** |

## Benchmarks

| Benchmark | Reference |
|---|---|
| GEO-Bench | Lacoste et al., NeurIPS 2023 Datasets & Benchmarks, https://arxiv.org/abs/2306.03831 |
| GeoLLM-Engine | Singh, Fore, Stamoulis, arXiv 2404.15500 (preprint) |
| GEOBench-VLM | Danish et al., arXiv 2411.19325 (preprint) |
| ThinkGeo | Shabbir et al., arXiv 2505.23752 (preprint) |
| Earth-Agent / Earth-Bench | Feng et al., ICLR 2026, https://iclr.cc/virtual/2026/poster/10008386 |
| UnivEARTH | Kao et al., Findings of ACL 2026, https://aclanthology.org/2026.findings-acl.124/ |
| TerraBench | Nguyen et al., arXiv 2606.13148 (preprint) |
| RAGTruth | Niu et al., ACL 2024, https://aclanthology.org/2024.acl-long.585/ |
| FActScore | Min et al., EMNLP 2023, https://aclanthology.org/2023.emnlp-main.741/ |
| AttributionBench | Li et al., Findings of ACL 2024, https://aclanthology.org/2024.findings-acl.886 |
| FaithEval | Ming et al., ICLR 2025, https://proceedings.iclr.cc/paper_files/paper/2025/hash/48404cd9ce03946c6b7177691f3267a1-Abstract-Conference.html |

## Data licenses

| Source | Terms | Reference |
|---|---|---|
| Hansen/UMD Global Forest Change | CC BY 4.0 | https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html |
| JRC GFC2020 | Free, without restriction of use (Copernicus Regulation). Acknowledgement required. Not described as CC BY. | https://forobs.jrc.ec.europa.eu/GFC |
| NASA FIRMS | Open data. Citation requested. No implied endorsement. | https://www.earthdata.nasa.gov/data/tools/firms · https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance |
| MGAP Bosques plantados (forest cartography) | Licencia de Datos Abiertos – Uruguay v0.1; mandatory source note | https://catalogodatos.gub.uy/dataset/mgap-bosques-plantados-forestacion |
| Apache-2.0 / CC BY 4.0 | License texts | https://www.apache.org/licenses/LICENSE-2.0 · https://creativecommons.org/licenses/by/4.0/ |

**Not verified, and therefore not claimed:**
- a named CC license for JRC GFC2020;
- whether NOAA-platform VIIRS products carry separate terms;
- the EOVC consortium membership;
- the venues of the arXiv preprints listed above.
