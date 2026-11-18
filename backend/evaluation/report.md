# LegalLens evaluation

## Overall (cases: Plain RAG: 36, CRAG: 36)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 92% | 92% |
| Answer accuracy | 81% | 92% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## english (cases: Plain RAG: 15, CRAG: 15)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 93% | 93% |
| Answer accuracy | 93% | 93% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## hindi (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 80% |
| Answer accuracy | 80% | 80% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## repealed_code (cases: Plain RAG: 6, CRAG: 6)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 100% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## out_of_scope (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | n/a | n/a |

## poor_retrieval (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 0% | 80% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | n/a |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | correct, hit (corpus) | correct, hit (corpus) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-theft | correct, hit (corpus) | correct, hit (corpus) |
| en-bnss-fir | correct, hit (corpus) | correct, hit (corpus) |
| en-bsa-electronic | correct, hit (corpus) | correct, hit (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | correct, hit (corpus) |
| en-tpa-lease | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-payment | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-overtime | wrong, miss (none) | wrong, miss (none) |
| en-osh-hours | correct, hit (corpus) | correct, hit (corpus) |
| en-ss-gratuity | correct, hit (corpus) | correct, hit (corpus) |
| en-ir-strike | correct, hit (corpus) | correct, hit (corpus) |
| hi-const-arrest | wrong, hit (corpus) | correct, hit (corpus) |
| hi-mta-deposit | correct, miss (corpus) | wrong, miss (corpus) |
| hi-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| hi-wages | correct, hit (corpus) | correct, hit (corpus) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-420 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-498a | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-154 | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-41 | correct, hit (corpus) | correct, hit (corpus) |
| rep-iea-65b | correct, hit (corpus) | correct, hit (corpus) |
| oos-sue | correct (none) | correct (none) |
| oos-sign | correct (none) | correct (none) |
| oos-us-law | correct (none) | correct (none) |
| oos-recipe | correct (none) | correct (none) |
| oos-plead | correct (none) | correct (none) |
| poor-rti | wrong (corpus) | correct (fallback) |
| poor-drunk-driving | wrong (corpus) | wrong (fallback) |
| poor-divorce | wrong (corpus) | correct (fallback) |
| poor-dv | wrong (corpus) | correct (fallback) |
| poor-gst | wrong (corpus) | correct (fallback) |
