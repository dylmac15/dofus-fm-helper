# Forgemage simulation results

Community-estimate Monte Carlo, **not official Dofus odds**. Ankama has never published SC/SN/EC rates. The helper's `ForgeSession.recommend()` picks each rune; a heuristic model samples the outcome; `apply_outcome` updates the item (reliquat first, then over/exo, then dump lines).

**Model:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.

**RNG seed:** 20260908. Re-run with `python -m fm_bot.simulate --seed 20260908`.

## How 2% dommages distance (Do Per Di) works here

Do Per Di is **+1% dist at 15 weight**. That sits under the 30-weight SC-only line, so the **first exo point** is a normal rune (SC/SN/EC in the 20× window). The **second exo point** is 2 × 15 = 30 weight past natural: **~1% SC, no SN** — the same family as exo PA/MP/PO. A **native 0–2%** line never crosses that 30-weight threshold, so both points stay normal. Once +1% or +2% exo is on the item, later SN/EC eat that over/exo first (Huzounet), which is why “ever reached 2%” is much higher than “ended at 2%”.

## Simple hat — perfect the natural lines

- **Item / id:** simple_hat
- **Goal:** Raise strength, intelligence, vitality (and keep initiative) to target.
- **Family:** concession  ·  **mode:** perfect
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 92.3% (277/300)
- **Throws:** median 40  ·  p90 101  ·  mean 50.1
- **Reliquat at end:** median 0.0  ·  p90 0.0
- **Stop reasons:** done 92.3% (277/300), attempts 7.7% (23/300)
- **Target lines reached (end of run):**
  - Force (`strength`) ≥ 80: 95.7% (287/300); ever reached 100.0% (300/300)
  - Intelligence (`intelligence`) ≥ 80: 94.0% (282/300); ever reached 100.0% (300/300)
  - Vitalité (`vitality`) ≥ 250: 93.0% (279/300); ever reached 94.3% (283/300)
  - Initiative (`initiative`) ≥ 200: 92.3% (277/300); ever reached 100.0% (300/300)
- **Example traces:**
  Example 1 (success):
    1. Ra Fo SC  strength → 18  sink 0  [low]
    2. Ra Fo SC  strength → 28  sink 0  [low]
    3. Ra Fo SC  strength → 38  sink 0  [low]
    4. Ra Fo SN  strength → 48  sink 0  [low]
    5. Ra Fo SC  strength → 58  sink 0  [low]
    6. Ra Fo SC  strength → 68  sink 0  [low]
    7. Ra Fo SN  strength → 78  sink 0  [low]
    8. Fo EC  strength → 78  sink 0  [high]
    9. Fo EC  strength → 78  sink 0  [high]
   10. Fo SN  strength → 79  sink 0  [high]
   11. Fo EC  strength → 79  sink 0  [high]
   12. Fo EC  strength → 79  sink 0  [high]
   13. Fo SN  strength → 80  sink 0  [high]
   14. Ra Ine SN  intelligence → 80  sink 0  [low]
   15. Ra Vi SN  vitality → 70  sink 0  [low]
   16. Ra Vi SC  vitality → 120  sink 0  [low]
   17. Ra Vi SC  vitality → 170  sink 0  [low]
   18. Ra Vi SN  vitality → 220  sink 0  [low]
   19. Pa Vi EC  vitality → 205  sink 0  [low]
   20. Pa Vi SC  vitality → 220  sink 0  [low]
   21. Pa Vi SC  vitality → 235  sink 0  [low]
   22. Pa Vi SC  vitality → 250  sink 0  [low]
   23. Ra Ini SN  initiative → 200  sink 0  [low]
   24. Ra Vi SC  vitality → 250  sink 0  [low]
  stop=done  throws=24  success=True  sink=0
  Example 2 (fail):
    1. Ra Fo SN  strength → 18  sink 0  [low]
    2. Ra Fo EC  strength → 18  sink 0  [low]
    3. Ra Fo SC  strength → 28  sink 0  [low]
    4. Ra Fo SN  strength → 38  sink 0  [low]
    5. Ra Fo SC  strength → 48  sink 0  [low]
    6. Ra Fo SN  strength → 58  sink 0  [low]
    7. Ra Fo SN  strength → 68  sink 0  [low]
    8. Ra Fo SN  strength → 78  sink 0  [low]
    9. Fo EC  strength → 78  sink 0  [high]
   10. Fo EC  strength → 78  sink 0  [high]
   11. Fo EC  strength → 78  sink 0  [high]
   12. Fo SN  strength → 79  sink 0  [high]
  … 96 more throws …
  109. Fo SC  strength → 80  sink 0  [high]
  110. Pa Ine EC  intelligence → 68  sink 0  [high]
  111. Ra Ine SC  intelligence → 78  sink 0  [low]
  112. Ine SN  intelligence → 79  sink 0  [high]
  113. Ine EC  intelligence → 78  sink 0  [high]
  114. Ine EC  intelligence → 77  sink 0  [high]
  115. Pa Ine EC  intelligence → 74  sink 0  [high]
  116. Pa Ine SN  intelligence → 77  sink 0  [high]
  117. Pa Ine SN  intelligence → 80  sink 0  [high]
  118. Pa Fo SN  strength → 76  sink 0  [high]
  119. Pa Fo EC  strength → 76  sink 0  [high]
  120. Pa Fo SN  strength → 79  sink 0  [high]
  stop=attempts  throws=120  success=False  sink=0

## Gelano — PA already on

- **Item / id:** gelano
- **Goal:** Item already at target (1 AP). Sanity check: 0 throws, done.
- **Family:** puits  ·  **mode:** perfect
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 100.0% (300/300)
- **Throws:** median 0  ·  p90 0  ·  mean 0.0
- **Reliquat at end:** median 0.0  ·  p90 0.0
- **Stop reasons:** done 100.0% (300/300)
- **Target lines reached (end of run):**
  - PA (`ap`) ≥ 1: 100.0% (300/300)
- **AP ≥ 1:** ended 100.0% (300/300); ever 100.0% (300/300)
- **Example traces:**
  Example 1 (success):
  (no throws — stop: done)

## Gelano — PA dropped, put it back

- **Item / id:** gelano_restore_pa
- **Goal:** Spend the ~100 well landing Ga Pa (native restore, not exo).
- **Family:** puits  ·  **mode:** repair
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 88.7% (266/300)
- **Throws:** median 1  ·  p90 1  ·  mean 1.0
- **Reliquat at end:** median 0.0  ·  p90 100.0
- **Stop reasons:** done 88.7% (266/300), empty_sink 11.3% (34/300)
- **Target lines reached (end of run):**
  - PA (`ap`) ≥ 1: 88.7% (266/300)
- **AP ≥ 1:** ended 88.7% (266/300); ever 88.7% (266/300)
- **Example traces:**
  Example 1 (success):
    1. Ga Pa SC  ap → 1  sink 100  [medium]
  stop=done  throws=1  success=True  sink=100
  Example 2 (fail):
    1. Ga Pa EC  ap → 0  sink 0  [medium]
  stop=empty_sink  throws=1  success=False  sink=0

## Gloursonne-like — exo PA (~1% SC)

- **Item / id:** gloursonne_exo_pa
- **Goal:** Stabilize natural lines, then exo +1 PA. Heavy exo = 1% SC, no SN.
- **Family:** concession  ·  **mode:** exo
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120  ·  empty-sink stop off (SC-only exo gamble)
- **Success (all targets):** 1.7% (5/300)
- **Throws:** median 120  ·  p90 120  ·  mean 118.7
- **Reliquat at end:** median 0.0  ·  p90 30.0
- **Stop reasons:** attempts 98.3% (295/300), done 1.7% (5/300)
- **Target lines reached (end of run):**
  - Vitalité (`vitality`) ≥ 150: 3.0% (9/300); ever reached 100.0% (300/300)
  - Force (`strength`) ≥ 40: 7.7% (23/300); ever reached 100.0% (300/300)
  - Sagesse (`wisdom`) ≥ 10: 7.3% (22/300); ever reached 100.0% (300/300)
  - PA (`ap`) ≥ 1: 2.3% (7/300); ever reached 63.3% (190/300)
- **AP ≥ 1:** ended 2.3% (7/300); ever 63.3% (190/300)
- **Example traces:**
  Example 1 (fail):
    1. Ra Fo SC  strength → 38  sink 0  [low]
    2. Fo EC  strength → 38  sink 0  [high]
    3. Fo SN  strength → 39  sink 0  [high]
    4. Fo SN  strength → 40  sink 0  [high]
    5. Pa Vi SN  vitality → 120  sink 0  [low]
    6. Pa Vi SC  vitality → 135  sink 0  [low]
    7. Pa Vi SN  vitality → 150  sink 0  [low]
    8. Pa Fo SC  strength → 37  sink 0  [low]
    9. Pa Fo SC  strength → 40  sink 0  [low]
   10. Ga Pa EC  ap → 0  sink 0  [sc_only]
   11. Ga Pa EC  ap → 0  sink 0  [sc_only]
   12. Ga Pa EC  ap → 0  sink 0  [sc_only]
  … 96 more throws …
  109. Ga Pa EC  ap → 0  sink 0  [sc_only]
  110. Ga Pa EC  ap → 0  sink 0  [sc_only]
  111. Ga Pa EC  ap → 0  sink 0  [sc_only]
  112. Ga Pa EC  ap → 0  sink 0  [sc_only]
  113. Ga Pa EC  ap → 0  sink 0  [sc_only]
  114. Ga Pa EC  ap → 0  sink 0  [sc_only]
  115. Ga Pa EC  ap → 0  sink 0  [sc_only]
  116. Ga Pa EC  ap → 0  sink 0  [sc_only]
  117. Ga Pa EC  ap → 0  sink 0  [sc_only]
  118. Ga Pa EC  ap → 0  sink 0  [sc_only]
  119. Ga Pa EC  ap → 0  sink 0  [sc_only]
  120. Ga Pa EC  ap → 0  sink 0  [sc_only]
  stop=attempts  throws=120  success=False  sink=0
  Example 2 (success):
    1. Ra Fo EC  strength → 28  sink 0  [low]
    2. Ra Fo SN  strength → 38  sink 0  [low]
    3. Fo EC  strength → 38  sink 0  [high]
    4. Fo EC  strength → 38  sink 0  [high]
    5. Fo SC  strength → 39  sink 0  [high]
    6. Fo SN  strength → 40  sink 0  [high]
    7. Ra Vi SC  vitality → 55  sink 0  [low]
    8. Ra Vi SN  vitality → 105  sink 0  [low]
    9. Pa Vi SN  vitality → 120  sink 0  [low]
   10. Pa Vi SN  vitality → 135  sink 0  [low]
   11. Pa Vi EC  vitality → 120  sink 0  [low]
   12. Pa Vi SC  vitality → 135  sink 0  [low]
   13. Pa Vi SC  vitality → 150  sink 0  [low]
   14. Ra Fo SN  strength → 34  sink 0  [low]
   15. Pa Fo SC  strength → 37  sink 0  [low]
   16. Pa Fo SC  strength → 40  sink 0  [low]
   17. Ra Vi SC  vitality → 150  sink 0  [low]
   18. Ga Pa SC  ap → 1  sink 0  [sc_only]
  stop=done  throws=18  success=True  sink=0

## Koutoulou-like — over vita with PA on

- **Item / id:** koutoulou_over_vita
- **Goal:** Over vitality to 350 while keeping native PA. SN/EC can eat PA.
- **Family:** puits  ·  **mode:** overmax
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 90.3% (271/300)
- **Throws:** median 15  ·  p90 26  ·  mean 15.8
- **Reliquat at end:** median 0.0  ·  p90 0.0
- **Stop reasons:** done 90.3% (271/300), empty_sink 9.7% (29/300)
- **Target lines reached (end of run):**
  - PA (`ap`) ≥ 1: 90.3% (271/300); ever reached 100.0% (300/300)
  - Vitalité (`vitality`) ≥ 350: 99.7% (299/300); ever reached 100.0% (300/300)
  - Intelligence (`intelligence`) ≥ 40: 100.0% (300/300)
  - Sagesse (`wisdom`) ≥ 15: 100.0% (300/300)
- **AP ≥ 1:** ended 90.3% (271/300); ever 100.0% (300/300)
- **Example traces:**
  Example 1 (success):
    1. Ra Ine SN  intelligence → 40  sink 0  [low]
    2. Ra Vi SN  vitality → 180  sink 0  [low]
    3. Ra Vi SN  vitality → 230  sink 0  [low]
    4. Ra Vi SN  vitality → 280  sink 0  [low]
    5. Ra Vi SC  vitality → 330  sink 0  [low]
    6. Ra Vi SC  vitality → 380  sink 0  [low]
    7. Ra Ine SN  intelligence → 20  sink 0  [low]
    8. Ra Ine SC  intelligence → 30  sink 0  [low]
    9. Ra Ine SN  intelligence → 40  sink 0  [low]
   10. Ra Vi SN  vitality → 330  sink 0  [low]
   11. Ra Vi SC  vitality → 380  sink 0  [low]
   12. Ra Ine SC  intelligence → 40  sink 0  [low]
  stop=done  throws=12  success=True  sink=0
  Example 2 (fail):
    1. Ra Ine SN  intelligence → 40  sink 0  [low]
    2. Ra Vi SN  vitality → 180  sink 0  [low]
    3. Ra Vi SN  vitality → 230  sink 0  [low]
    4. Ra Vi SN  vitality → 280  sink 0  [low]
    5. Ra Vi SN  vitality → 330  sink 0  [low]
    6. Ra Vi SN  vitality → 380  sink 99  [low]
    7. Ra Ine SC  intelligence → 10  sink 99  [low]
    8. Ra Ine SC  intelligence → 20  sink 99  [low]
    9. Ra Ine SC  intelligence → 30  sink 99  [low]
   10. Ra Ine SC  intelligence → 40  sink 99  [low]
   11. Ga Pa EC  ap → 0  sink 0  [medium]
  stop=empty_sink  throws=11  success=False  sink=0

## Koutoulou-like — PA dropped + sink 100, over vita

- **Item / id:** koutoulou_over_vita_pa_dropped
- **Goal:** Park the PA well into vita, restore PA, then keep overmaging vita.
- **Family:** puits  ·  **mode:** overmax
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 22.7% (68/300)
- **Throws:** median 6  ·  p90 9  ·  mean 6.8
- **Reliquat at end:** median 60.0  ·  p90 70.0
- **Stop reasons:** empty_sink 77.3% (232/300), done 22.7% (68/300)
- **Target lines reached (end of run):**
  - PA (`ap`) ≥ 1: 22.7% (68/300)
  - Vitalité (`vitality`) ≥ 350: 95.3% (286/300); ever reached 100.0% (300/300)
  - Intelligence (`intelligence`) ≥ 40: 100.0% (300/300)
  - Sagesse (`wisdom`) ≥ 15: 100.0% (300/300)
- **AP ≥ 1:** ended 22.7% (68/300); ever 22.7% (68/300)
- **Example traces:**
  Example 1 (fail):
    1. Ra Ine SN  intelligence → 40  sink 90  [low]
    2. Ra Vi SC  vitality → 230  sink 90  [low]
    3. Ra Vi SN  vitality → 280  sink 80  [low]
    4. Ra Vi SN  vitality → 330  sink 70  [low]
    5. Ra Vi SN  vitality → 380  sink 60  [low]
  stop=empty_sink  throws=5  success=False  sink=60
  Example 2 (success):
    1. Ra Ine EC  intelligence → 30  sink 90  [low]
    2. Ra Ine SC  intelligence → 40  sink 90  [low]
    3. Ra Vi SC  vitality → 230  sink 90  [low]
    4. Ra Vi SC  vitality → 280  sink 90  [low]
    5. Ra Vi SC  vitality → 330  sink 90  [low]
    6. Ra Vi SN  vitality → 380  sink 80  [low]
    7. Ga Pa SC  ap → 1  sink 80  [medium]
  stop=done  throws=7  success=True  sink=80

## Strigide-like — over ré cri, dump heals

- **Item / id:** strigide_concession
- **Goal:** Concede heals at 8 and push critical resist to 12 (over).
- **Family:** concession  ·  **mode:** overmax
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 99.7% (299/300)
- **Throws:** median 16  ·  p90 30  ·  mean 17.8
- **Reliquat at end:** median 0.0  ·  p90 1.0
- **Stop reasons:** done 99.7% (299/300), empty_sink 0.3% (1/300)
- **Target lines reached (end of run):**
  - Résistance Critique (`crit_resist`) ≥ 12: 99.7% (299/300); ever reached 100.0% (300/300)
  - Soin (`heals`) ≥ 8: 99.7% (299/300); ever reached 100.0% (300/300)
  - Vitalité (`vitality`) ≥ 150: 99.7% (299/300)
  - Puissance (`power`) ≥ 25: 100.0% (300/300)
- **Example traces:**
  Example 1 (success):
    1. Pa Pui SC  power → 21  sink 0  [low]
    2. Pa Pui SC  power → 24  sink 0  [low]
    3. Pui SN  power → 25  sink 0  [high]
    4. Ra Ré Cri SN  crit_resist → 15  sink 0  [low]
    5. Ra Vi EC  vitality → 10  sink 0  [low]
    6. Ra Vi SN  vitality → 60  sink 0  [low]
    7. Ra Vi SC  vitality → 110  sink 0  [low]
    8. Pa Vi SC  vitality → 125  sink 0  [low]
    9. Pa Vi SN  vitality → 140  sink 1  [low]
   10. Vi EC  vitality → 140  sink 0  [medium]
   11. Vi EC  vitality → 135  sink 0  [high]
   12. Pa Vi SC  vitality → 150  sink 0  [low]
  … 9 more throws …
   22. Vi EC  vitality → 140  sink 0  [high]
   23. Vi SN  vitality → 145  sink 1  [high]
   24. Vi EC  vitality → 145  sink 0  [medium]
   25. Vi EC  vitality → 140  sink 0  [high]
   26. Vi SN  vitality → 145  sink 1  [high]
   27. Vi SN  vitality → 150  sink 0  [medium]
   28. Ra Ré Cri SN  crit_resist → 15  sink 0  [low]
   29. Ra Vi SN  vitality → 100  sink 0  [low]
   30. Ra Vi SC  vitality → 150  sink 0  [low]
   31. Ra Ré Cri SN  crit_resist → 20  sink 0  [low]
   32. Ra Vi SC  vitality → 100  sink 0  [low]
   33. Ra Vi SC  vitality → 150  sink 0  [low]
  stop=done  throws=33  success=True  sink=0
  Example 2 (fail):
    1. Pa Pui SN  power → 21  sink 0  [low]
    2. Pa Pui SN  power → 24  sink 0  [low]
    3. Pui SN  power → 25  sink 0  [high]
    4. Ra Ré Cri SN  crit_resist → 15  sink 0  [low]
    5. Pa Pui SN  power → 23  sink 0  [low]
    6. Pui EC  power → 23  sink 0  [high]
    7. Pui EC  power → 23  sink 0  [high]
    8. Pui SC  power → 24  sink 0  [high]
    9. Pui SN  power → 25  sink 0  [high]
   10. Ra Ré Cri EC  crit_resist → 0  sink 0  [low]
   11. Ra Ré Cri SN  crit_resist → 10  sink 0  [low]
   12. Ra Ré Cri SN  crit_resist → 20  sink 0  [low]
   13. Ra Pui EC  power → 4  sink 0  [low]
   14. Ra Pui SN  power → 14  sink 0  [low]
   15. Ra Pui SN  power → 24  sink 0  [low]
   16. Pui SC  power → 25  sink 0  [high]
   17. Ra Ré Cri SN  crit_resist → 10  sink 0  [low]
   18. Ra Ré Cri SN  crit_resist → 20  sink 0  [low]
   19. Ra Pui EC  power → 5  sink 0  [low]
   20. Ra Pui EC  power → 5  sink 0  [low]
   21. Ra Pui SN  power → 15  sink 0  [low]
   22. Ra Pui SN  power → 25  sink 0  [low]
  stop=empty_sink  throws=22  success=False  sink=0

## Custom — exo 2% dommages distance

- **Item / id:** dist_exo_2pct
- **Goal:** Generic vita/str/wisdom piece with no native % dist. Target +2% dist (Do Per Di, 15 weight/pt). First point is a normal rune; the 2nd is ≥30 weight past natural (~1% SC).
- **Family:** concession  ·  **mode:** exo
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 150
- **Success (all targets):** 0.7% (2/300)
- **Throws:** median 150  ·  p90 150  ·  mean 125.3
- **Reliquat at end:** median 0.0  ·  p90 10.0
- **Stop reasons:** attempts 56.7% (170/300), empty_sink 42.7% (128/300), done 0.7% (2/300)
- **Target lines reached (end of run):**
  - Vitalité (`vitality`) ≥ 200: 0.7% (2/300); ever reached 100.0% (300/300)
  - Force (`strength`) ≥ 40: 43.7% (131/300); ever reached 100.0% (300/300)
  - Sagesse (`wisdom`) ≥ 20: 0.7% (2/300); ever reached 100.0% (300/300)
  - % Dommage Distance (`pct_ranged_damage`) ≥ 2: 2.7% (8/300); ever reached 53.7% (161/300)
- **% dommages distance (Do Per Di):**
  - ended at 0%: 67.0% (201/300); peak ≥ 0%: 100.0% (300/300)
  - ended at 1%: 30.3% (91/300); peak ≥ 1%: 100.0% (300/300)
  - ended at 2%: 2.7% (8/300); peak ≥ 2%: 53.7% (161/300)
- **Example traces:**
  Example 1 (fail):
    1. Ra Fo SN  strength → 30  sink 0  [low]
    2. Ra Fo SN  strength → 40  sink 0  [low]
    3. Pa Sa EC  wisdom → 15  sink 0  [low]
    4. Pa Sa SC  wisdom → 18  sink 0  [low]
    5. Sa EC  wisdom → 18  sink 0  [medium]
    6. Sa SN  wisdom → 19  sink 0  [medium]
    7. Sa EC  wisdom → 19  sink 0  [medium]
    8. Sa SC  wisdom → 20  sink 0  [medium]
    9. Pa Fo SC  strength → 35  sink 0  [low]
   10. Pa Fo SN  strength → 38  sink 0  [low]
   11. Fo EC  strength → 37  sink 0  [high]
   12. Pa Fo EC  strength → 34  sink 0  [low]
  … 109 more throws …
  122. Do Per Di EC  pct_ranged_damage → 0  sink 0  [sc_only]
  123. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
  124. Do Per Di EC  pct_ranged_damage → 0  sink 0  [sc_only]
  125. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
  126. Do Per Di EC  pct_ranged_damage → 0  sink 0  [sc_only]
  127. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
  128. Do Per Di SC  pct_ranged_damage → 2  sink 0  [sc_only]
  129. Ra Fo SN  strength → 10  sink 5  [low]
  130. Ra Fo SC  strength → 20  sink 5  [low]
  131. Ra Fo SC  strength → 30  sink 5  [low]
  132. Ra Fo EC  strength → 30  sink 10  [low]
  133. Ra Fo SC  strength → 40  sink 10  [low]
  stop=empty_sink  throws=133  success=False  sink=10
  Example 2 (success):
    1. Ra Fo SN  strength → 30  sink 0  [low]
    2. Ra Fo SN  strength → 40  sink 0  [low]
    3. Pa Sa SN  wisdom → 18  sink 0  [low]
    4. Sa SN  wisdom → 19  sink 0  [medium]
    5. Sa SC  wisdom → 20  sink 0  [medium]
    6. Fo EC  strength → 37  sink 0  [high]
    7. Pa Fo SN  strength → 40  sink 0  [low]
    8. Sa SN  wisdom → 20  sink 0  [medium]
    9. Pa Fo SC  strength → 40  sink 0  [low]
   10. Ra Vi SN  vitality → 50  sink 0  [low]
   11. Ra Vi SN  vitality → 100  sink 0  [low]
   12. Ra Vi EC  vitality → 50  sink 0  [low]
  … 21 more throws …
   34. Ra Vi SN  vitality → 185  sink 0  [low]
   35. Pa Vi SN  vitality → 200  sink 0  [low]
   36. Ra Fo SC  strength → 37  sink 0  [low]
   37. Pa Fo SN  strength → 40  sink 0  [low]
   38. Pa Vi SN  vitality → 200  sink 0  [low]
   39. Pa Fo SC  strength → 40  sink 0  [low]
   40. Do Per Di SC  pct_ranged_damage → 1  sink 0  [low]
   41. Do Per Di EC  pct_ranged_damage → 0  sink 0  [sc_only]
   42. Do Per Di SC  pct_ranged_damage → 1  sink 0  [low]
   43. Do Per Di EC  pct_ranged_damage → 0  sink 0  [sc_only]
   44. Do Per Di SC  pct_ranged_damage → 1  sink 0  [low]
   45. Do Per Di SC  pct_ranged_damage → 2  sink 0  [sc_only]
  stop=done  throws=45  success=True  sink=0

## Same item — native max 2% dist (perfect the line)

- **Item / id:** dist_natural_2pct
- **Goal:** Same vita/str/wisdom, but % dist is a natural 0–2 line at 0. Both points stay under the 30-weight SC-only threshold.
- **Family:** concession  ·  **mode:** perfect
- **Heuristic:** Reliable window (~20× bonus): 40% SC / 50% SN / 10% EC; near the 20× edge more EC; past 20× 12/38/50; heavy over/exo ≥30 weight past natural: 1% SC, no SN.
- **Runs:** 300  ·  **throw cap:** 120
- **Success (all targets):** 96.3% (289/300)
- **Throws:** median 33  ·  p90 58  ·  mean 36.0
- **Reliquat at end:** median 0.0  ·  p90 0.0
- **Stop reasons:** done 96.3% (289/300), empty_sink 3.3% (10/300), attempts 0.3% (1/300)
- **Target lines reached (end of run):**
  - Vitalité (`vitality`) ≥ 200: 96.7% (290/300)
  - Force (`strength`) ≥ 40: 99.7% (299/300); ever reached 100.0% (300/300)
  - Sagesse (`wisdom`) ≥ 20: 96.7% (290/300); ever reached 97.3% (292/300)
  - % Dommage Distance (`pct_ranged_damage`) ≥ 2: 96.7% (290/300); ever reached 100.0% (300/300)
- **% dommages distance (Do Per Di):**
  - ended at 0%: 0.7% (2/300); peak ≥ 0%: 100.0% (300/300)
  - ended at 1%: 2.7% (8/300); peak ≥ 1%: 100.0% (300/300)
  - ended at 2%: 96.7% (290/300); peak ≥ 2%: 100.0% (300/300)
- **Example traces:**
  Example 1 (success):
    1. Ra Fo SC  strength → 30  sink 0  [low]
    2. Ra Fo SN  strength → 40  sink 0  [low]
    3. Do Per Di EC  pct_ranged_damage → 0  sink 0  [low]
    4. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
    5. Do Per Di SN  pct_ranged_damage → 2  sink 0  [low]
    6. Ra Fo SN  strength → 25  sink 14  [low]
    7. Ra Fo SN  strength → 35  sink 4  [low]
    8. Pa Fo SN  strength → 38  sink 1  [low]
    9. Fo EC  strength → 38  sink 0  [medium]
   10. Fo EC  strength → 37  sink 0  [high]
   11. Pa Fo SN  strength → 40  sink 0  [low]
   12. Pa Sa SN  wisdom → 14  sink 0  [low]
  … 35 more throws …
   48. Ra Fo SC  strength → 20  sink 0  [low]
   49. Ra Fo SN  strength → 30  sink 0  [low]
   50. Ra Fo SN  strength → 40  sink 0  [low]
   51. Ra Vi SN  vitality → 150  sink 0  [low]
   52. Ra Vi SN  vitality → 200  sink 0  [low]
   53. Ra Fo SN  strength → 30  sink 0  [low]
   54. Ra Fo SN  strength → 40  sink 0  [low]
   55. Ra Vi SN  vitality → 150  sink 0  [low]
   56. Ra Vi SN  vitality → 200  sink 0  [low]
   57. Ra Fo SN  strength → 30  sink 0  [low]
   58. Ra Fo SC  strength → 40  sink 0  [low]
   59. Ra Vi SC  vitality → 200  sink 0  [low]
  stop=done  throws=59  success=True  sink=0
  Example 2 (fail):
    1. Ra Fo SC  strength → 30  sink 0  [low]
    2. Ra Fo SN  strength → 40  sink 0  [low]
    3. Do Per Di EC  pct_ranged_damage → 0  sink 0  [low]
    4. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
    5. Do Per Di SN  pct_ranged_damage → 2  sink 0  [low]
    6. Ra Fo SC  strength → 25  sink 0  [low]
    7. Ra Fo SC  strength → 35  sink 0  [low]
    8. Pa Fo EC  strength → 32  sink 0  [low]
    9. Pa Fo SC  strength → 35  sink 0  [low]
   10. Pa Fo SN  strength → 38  sink 0  [low]
   11. Fo EC  strength → 37  sink 0  [high]
   12. Pa Fo SN  strength → 40  sink 0  [low]
  … 27 more throws …
   40. Pa Fo SC  strength → 35  sink 4  [low]
   41. Pa Fo EC  strength → 35  sink 1  [low]
   42. Pa Fo SN  strength → 38  sink 1  [low]
   43. Fo EC  strength → 38  sink 0  [medium]
   44. Fo EC  strength → 37  sink 0  [high]
   45. Pa Fo SN  strength → 40  sink 0  [low]
   46. Do Per Di EC  pct_ranged_damage → 0  sink 0  [low]
   47. Do Per Di SN  pct_ranged_damage → 1  sink 0  [low]
   48. Do Per Di SC  pct_ranged_damage → 2  sink 0  [low]
   49. Ra Fo SN  strength → 20  sink 14  [low]
   50. Ra Fo SN  strength → 30  sink 4  [low]
   51. Ra Fo SN  strength → 40  sink 0  [low]
  stop=empty_sink  throws=51  success=False  sink=0

---

If a real workshop disagrees with a rate here, trust the game — the model is a teaching aid for rune order and over/exo risk, not a kama forecast.
