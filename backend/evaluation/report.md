# LegalLens evaluation

## Overall (31 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 57% | 52% |
| Answer accuracy | 55% | 52% |
| Citation validity | 100% | 100% |

## english (11 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 64% | 54% |
| Answer accuracy | 64% | 54% |
| Citation validity | 100% | 100% |

## hindi (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 20% | 20% |
| Answer accuracy | 20% | 20% |
| Citation validity | 100% | 100% |

## repealed_code (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 100% |
| Answer accuracy | 80% | 100% |
| Citation validity | 100% | 100% |

## out_of_scope (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 100% | 100% |
| Citation validity | 100% | 100% |

## poor_retrieval (5 cases)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 0% | 0% |
| Citation validity | 100% | 100% |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | error (HTTPStatusError) | wrong, miss (corpus_and_fallback) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | error (HTTPStatusError) | correct, hit (corpus) |
| en-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-theft | wrong, miss (corpus) | wrong, miss (corpus) |
| en-bnss-fir | wrong, miss (corpus) | wrong, miss (corpus) |
| en-bsa-electronic | wrong, miss (corpus) | wrong, miss (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | error (HTTPStatusError) |
| en-tpa-lease | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-payment | wrong, miss (corpus) | error (HTTPStatusError) |
| en-wages-overtime | error (HTTPStatusError) | wrong, miss (corpus) |
| en-osh-hours | error (HTTPStatusError) | wrong, miss (fallback) |
| en-ss-gratuity | correct, hit (corpus) | correct, hit (corpus) |
| en-ir-strike | correct, hit (corpus) | correct, hit (corpus_and_fallback) |
| hi-const-arrest | wrong, miss (corpus) | wrong, miss (corpus) |
| hi-mta-deposit | wrong, miss (corpus) | wrong, miss (corpus) |
| hi-cpa-complaint | wrong, miss (corpus) | wrong, miss (corpus) |
| hi-wages | wrong, miss (corpus) | wrong, miss (fallback) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-420 | wrong, miss (corpus) | error (HTTPStatusError) |
| rep-ipc-498a | error (HTTPStatusError) | correct, hit (corpus) |
| rep-crpc-154 | correct, hit (corpus) | error (HTTPStatusError) |
| rep-crpc-41 | correct, hit (corpus) | correct, hit (corpus) |
| rep-iea-65b | correct, hit (corpus) | error (HTTPStatusError) |
| oos-sue | correct (corpus) | correct (corpus) |
| oos-sign | correct (corpus) | correct (corpus) |
| oos-us-law | correct (corpus) | correct (corpus) |
| oos-recipe | correct (corpus) | correct (corpus) |
| oos-plead | correct (corpus) | correct (corpus) |
| poor-rti | wrong (corpus) | wrong (fallback) |
| poor-drunk-driving | wrong (corpus) | wrong (fallback) |
| poor-divorce | wrong (corpus) | wrong (corpus) |
| poor-dv | wrong (corpus) | wrong (corpus) |
| poor-gst | wrong (corpus) | wrong (corpus) |

10 case runs failed after retries and are excluded from the metrics: en-const-arrest (HTTPStatusError), en-const-education (HTTPStatusError), en-wages-overtime (HTTPStatusError), en-osh-hours (HTTPStatusError), rep-ipc-498a (HTTPStatusError), en-mta-deposit (HTTPStatusError), en-wages-payment (HTTPStatusError), rep-ipc-420 (HTTPStatusError), rep-crpc-154 (HTTPStatusError), rep-iea-65b (HTTPStatusError)
