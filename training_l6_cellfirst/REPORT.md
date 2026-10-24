# CCC42 Level 6 — Cell-First: итог эксперимента

**15770 → 15721 тактов; −49; улучшено 40/540 cases. Полная локальная валидация PASS.**

Реализованы и применены универсальный C++20 Cell-First Scheduler, геометрические конфигурации, макрохорды на 2–4 такта, двунаправленный мост, назначение клеток с LNS/обратной связью и точный ремонт. Однако поиск новых полных программ с нуля не дал подтвержденного выигрыша. Реальное улучшение получено в основном Cell-Assignment LNS, дополненным существующим acceptance graph и точными ограниченными моделями. Прорыв по устойчивому периоду производства не установлен; глобальная минимальность суммы не доказана.

## LEVEL 6 MAIN DATASETS

| Набор | Проверенный baseline | Best | Saved | Улучшено |
|---|---:|---:|---:|---:|
| MEDIUM | 5917 | 5915 | 2 | 2 / 210 |
| LARGE | 5112 | 5092 | 20 | 18 / 190 |
| ENORMOUS | 4741 | 4714 | 27 | 20 / 140 |
| TOTAL | 15770 | 15721 | 49 | 40 / 540 |

Baseline собран покейсово из всех полных локальных банков и отдельно именованных Medium-кандидатов, прошедших независимую проверку. Проверены предыдущие Codex-эксперименты, Antigravity/experiment_ultra и исторические level-6 банки. Найденный минимум точно совпал с 15770. Источники каждого case, отвергнутые программы и SHA256 сохранены в experiments/. Невалидные near-miss не включались в baseline или best.

## Атрибуция без перекрытий

| Первый реально улучшивший checkpoint | Тактов |
|---|---:|
| cell_assignment_graph | 40 |
| command_lns_repair_graph | 2 |
| acceptance_symmetry_graph | 2 |
| expanded_exact_repair | 5 |

Cell-First beam / ray scheduler: **0**; отдельные collinear macros: **0**; bidirectional: **0**; новые многокопийные циклы: **0**; ограниченный targeted CP с 3–4 свободными эмиттерами: **0**. Cell-assignment и граф указаны совместно: выигрыш не посчитан повторно как отдельный вклад DP. Два исторических symmetry/graph выигрыша — повторное комбинирование существующих программ, не новые физические стратегии. Command-level repair выделен отдельно. Расширенный exact repair разрешает все шесть эмиттеров в выбранной малой подзадаче.

Суммарное сокращение времени первого принятия: 34; изменение стоимости после первого принятия: 15. Однокопийные cases целиком входят в первую категорию. Устойчивый более быстрый цикл нельзя выводить из сокращения setup или единичного транзиента.

## Реализованные модели и ограничения

- C++ использует до 8 слов по 64 бита, все 6 эмиттеров и полное релевантное состояние target|skirting. Каждая команда и промежуточное принятие моделируются точно. После принятия релевантная материя пуста; позы и активность сохраняются.
- Cell geometry хранит рельсовые координаты каждой клетки для всех эмиттеров, 15 возможных пар, 20 троек и 3 семейства. Генератор начинает с незаполненных/ошибочных клеток; подбирает пары, дополнительные лучи и клипперы в пределах достижимости.
- Beam сохраняет различающиеся материю, геометрию и число активных эмиттеров. Геометрические оценки не объявляются допустимыми нижними границами. Глобальный A* не реализован; нижние границы приведены отдельно.
- Макросы на 2/3/4 такта используют разные моменты переключений/движений, допускают временные загрязнения и уничтожение target. Дальние конфигурации направляют короткие физически исполнимые префиксы. Дополнительный master строит библиотеку хорд с клипперами и непараллельных пар.
- Обратная регрессия сохраняет несколько требований ones/zeros и поз; прямой шестилучевой мост проверяет точную совместимость и затем переигрывает всю программу. Глубина регрессии ограничена 5, прямые макромосты — 4; это эвристический, неполный поиск.
- Cell-assignment LNS назначает дефектной клетке 2 луча для создания или 3 для стирания; временная подзадача строит допустимые пути эмиттеров. Точный симулятор дает обратную связь по всем клеткам и всем принятиям. LNS также имеет обычные командные мутации: его выигрыш нельзя полностью приписывать одному геометрическому оператору.
- Acceptance graph/DP переиспользован из training_medium_codex_v2 без изменения исходника. Ребра содержат actual start/end, программу и 1–4 принятия. DP минимизирует полную K-copy стоимость при свободной конечной позе. Проверяются отдельные обратные переходы, многокопийные ребра и симметрии противоположных эмиттеров.
- Near repair ранжирует эмиттеры и временные окна по ошибочным клеткам; затем расширяет свободные эмиттеры. CP задает точную материю, iff-принятие и очистку на каждом такте. Полные локальные модели запускаются только для выбранных малых cases/горизонтов, не как наивная модель всех 540 задач.

## Пилот, ablation и адаптивный бюджет

Диагностический пилот: Medium 162,133,181,198,59; Large 144,65,101,78,147,19,125,29; Enormous 2,65,1,104,133,79,114,126. Выбор смешивает долю повторных H2, стоимость setup и target-клетки на интервал. Исходные метрики — experiments/diagnostics.json.

| Этап / алгоритм | Записей | Выигрыш относительно baseline этапа | Query/этапное время, с | Evaluations |
|---|---:|---:|---:|---:|
| assignment_all_enormous / cell_assignment_graph | 140 | 18 | 158.314 | 654969407 |
| assignment_all_large / cell_assignment_graph | 190 | 11 | 158.670 | 587963004 |
| assignment_all_medium / cell_assignment_graph | 210 | 2 | 139.673 | 392902014 |
| assignment_deep_enormous / cell_assignment_graph | 19 | 6 | 52.828 | 228062543 |
| assignment_deep_large / cell_assignment_graph | 12 | 2 | 31.024 | 126868870 |
| assignment_pilot_enormous / cell_assignment_graph | 8 | 1 | 7.373 | 34331015 |
| assignment_pilot_enormous / command_lns_graph | 8 | 0 | 7.681 | 41280636 |
| assignment_pilot_large / cell_assignment_graph | 8 | 0 | 10.371 | 46737354 |
| assignment_pilot_large / command_lns_graph | 8 | 0 | 10.369 | 58061173 |
| assignment_pilot_medium / cell_assignment_graph | 5 | 0 | 6.007 | 24449860 |
| assignment_pilot_medium / command_lns_graph | 5 | 0 | 6.756 | 36786556 |
| bidirectional_pilot / reverse_six_bridge | 21 | 0 | 15.385 | 12268532 |
| bidirectional_pilot / reverse_geometry_bridge | 21 | 0 | 14.803 | 8761235 |
| bidirectional_pilot / reverse_chord_bridge | 21 | 0 | 13.940 | 9990590 |
| chord_library_pilot_enormous / cellfirst_chord_library | 8 | 0 | 1.710 | 2722831 |
| chord_library_pilot_large / cellfirst_chord_library | 8 | 0 | 1.174 | 1990645 |
| chord_library_pilot_medium / cellfirst_chord_library | 5 | 0 | 0.428 | 722733 |
| constructive_stage_c_enormous / constructive_command | 8 | 0 | 8.881 | 32161792 |
| constructive_stage_c_enormous / constructive_cellfirst | 8 | 0 | 9.623 | 1963132 |
| constructive_stage_c_enormous / constructive_chord | 8 | 0 | 8.174 | 6473239 |
| constructive_stage_c_enormous / constructive_cellfirst_chord | 8 | 0 | 9.615 | 1688086 |
| constructive_stage_c_large / constructive_command | 8 | 0 | 6.854 | 31649792 |
| constructive_stage_c_large / constructive_cellfirst | 8 | 0 | 9.483 | 3155929 |
| constructive_stage_c_large / constructive_chord | 8 | 0 | 7.034 | 5763762 |
| constructive_stage_c_large / constructive_cellfirst_chord | 8 | 0 | 9.611 | 2510082 |
| constructive_stage_c_medium / constructive_command | 5 | 0 | 4.982 | 24870677 |
| constructive_stage_c_medium / constructive_cellfirst | 5 | 0 | 5.783 | 3558008 |
| constructive_stage_c_medium / constructive_chord | 5 | 0 | 4.953 | 4567292 |
| constructive_stage_c_medium / constructive_cellfirst_chord | 5 | 0 | 6.004 | 2654467 |
| exact_polish / expanded_exact_polish | 22 | 0 | 78.294 | 644218 |
| frontier_deep_medium / frontier_symmetry_and_bridges | 12 | 0 | 3.964 | 2550988 |
| frontier_distinct_medium / frontier_symmetry_and_bridges | 12 | 0 | 46.028 | 194587143 |
| history_symmetry_all_enormous / frontier_symmetry_and_bridges | 140 | 1 | 7.917 | 0 |
| history_symmetry_all_large / frontier_symmetry_and_bridges | 190 | 1 | 14.727 | 0 |
| pilot / command_beam | 21 | 0 | 9.713 | 5468160 |
| pilot / cellfirst | 21 | 0 | 9.164 | 3683489 |
| pilot / macro_chord | 21 | 0 | 9.331 | 3480369 |
| pilot / cellfirst_chord | 21 | 0 | 9.514 | 2608136 |
| ray_library_discovery_enormous / cellfirst_chord_library | 8 | 0 | 8.338 | 4709907 |
| ray_library_discovery_large / cellfirst_chord_library | 8 | 0 | 4.519 | 3526200 |
| ray_library_discovery_medium / cellfirst_chord_library | 5 | 0 | 1.316 | 1448072 |
| ray_library_full_pilot_enormous / cellfirst_chord_library | 8 | 0 | 5.662 | 3042323 |
| ray_library_full_pilot_large / cellfirst_chord_library | 8 | 0 | 3.012 | 2470508 |
| ray_library_full_pilot_medium / cellfirst_chord_library | 5 | 0 | 0.864 | 961588 |
| repair_enormous / command_lns | 12 | 1 | 22.449 | 99761576 |
| repair_enormous / targeted_cp | 12 | 1 | 11.249 | 0 |
| repair_enormous / ordinary_cp | 12 | 1 | 27.337 | 0 |
| repair_expanded / expanded_exact_repair | 24 | 5 | 87.152 | 392138 |
| repair_stage_b / command_lns | 24 | 1 | 34.329 | 111743568 |
| repair_stage_b / targeted_cp | 24 | 1 | 5.216 | 0 |
| repair_stage_b / ordinary_cp | 24 | 1 | 6.753 | 10991 |
| reverse_comparison / reverse_old | 21 | 1 | 2.834 | 46740970 |
| reverse_comparison / reverse_fixed | 21 | 1 | 2.847 | 47232490 |

Строки разных этапов не складываются для атрибуции: один case может встречаться несколько раз, а baseline этапов обновляется. Фактическая неперекрывающаяся атрибуция — таблица checkpoints выше. Внутри пилота четыре beam-варианта получают одинаковые 250 ms/query, width=24 и одинаковые anchors/seeds. Cell-assignment vs command LNS: 450 ms/query, одинаковые исходные графы и горизонты. Bidirectional arms: 400 ms/query, width=32. Cold-start arms: 1200 ms, width=24. Ремонт сравнивает command LNS, targeted CP и обычный CP на одном near-кандидате с одинаковым лимитом решения; CP-построение модели измерено дополнительно внутри runtime. Такие лимиты сопоставимы по потолку, но фактическое время бывает меньше при раннем завершении.

Полный проход assignment: Medium 180 ms/query, Large 250 ms/query, Enormous 500 ms/query. Последующее углубление победителей: Large 1000 ms/query, Enormous 1500 ms/query. Затем exact repair 4 s и polish 6 s на выбранных малых задачах. Основной ресурс перенаправлен в Large/Enormous после реальных выигрышей. Время разных процессов частично перекрывалось; сумму query-time нельзя выдавать за длительность всей сессии.

| Набор | Full-pass saved / query seconds | Saved ticks / s |
|---|---:|---:|
| medium | 2 / 139.673 | 0.0143 |
| large | 11 / 158.670 | 0.0693 |
| enormous | 18 / 158.314 | 0.1137 |

Результат assignment-пилота — один удачный Enormous case; он не доказывает превосходства Cell-First или геометрического оператора. Последующие проходы сравниваются с актуальным более сильным best. Первоначальный frontier_deep включал известные тождественные ребра; этот диагностический недостаток исправлен в frontier_distinct, где donor.start != actual start. Выигрыша на этом distinct-мостовом проходе нет.

## Исследовательские наблюдения

| Набор | Новых target-клеток / tick, до → после | Доля повторных H2 на target, до → после |
|---|---:|---:|
| medium | 4.1993 → 4.2007 | 19.1547% → 19.1415% |
| large | 4.0593 → 4.0754 | 29.6171% → 29.4366% |
| enormous | 3.9540 → 3.9782 | 37.3839% → 37.0831% |

Доля повторов определена как H2-клетки на уже существующей target-материи / все H2 target-клетки. Это не число всех фотонных попаданий и не доказанная бесполезность пересечения. Изменение вспомогательной метрики не использовано как самостоятельный успех.

Максимум в проверенных итоговых траекториях: 36 новых target-клеток за один такт (enormous case 2, tick 2); opposed chord axes = [0, 1]. Точные позы, команды, разрушения и skirting для 200 продуктивных конфигураций сохранены в geometry/productive_configurations.json. Эти конфигурации наблюдаются в проверенных программах; это не приписывание их изобретения новому движку.

Улучшения по числу копий: {1: 23, 2: 10, 3: 1, 4: 2, 5: 1, 6: 2, 7: 1}. Наиболее результативным оказался локальный ремонт коротких Large/Enormous и setup/однокопийных траекторий. Новый холодный Cell-First поиск не показал класса паттернов с доказанным преимуществом над incumbent.

Почему большинство cases не улучшены: в ограниченных beam/макрогоризонтах не найден более короткий полностью корректный маршрут; полезная статическая конфигурация не гарантирует дешевого перехода с очисткой skirting. Распределение материала и поз создает большие фронтиры, а эвристический beam отбрасывает потенциально полезные временные ухудшения. Это рабочие объяснения/ограничения реализации, не доказательство невозможности. Холодные near-кандидаты с записанной ошибкой ≤16 в этом пилоте не получены; многие близкие кандидаты LNS требуют совместного изменения более 3–4 эмиттеров, что подтверждается разницей между ограниченным и расширенным repair.

## Что действительно доказано

Для каждой target-клетки вычислено минимальное время активации ее луча каждым эмиттером из начальной позы: циклическое расстояние + одно переключение. Для двух попаданий нужно не меньше второй порядковой статистики этих шести времен; максимум по клеткам дает нижнюю границу первого принятия τ. Следовательно total ≥ τ+K−1.

В одном такте каждая из 12 непараллельных пар эмиттеров пересекается максимум в одной target-клетке. Каждая из 3 противоположных пар покрывает не более максимальной target-хорды своего семейства C_a. Поэтому H2 target ≤ U=min(NT,12+Σ C_a), а total ≥ ceil(K·NT/U). Это допустимые, обычно слабые границы; повторное создание уничтоженной материи не ослабляет доказательство.

Простая нижняя граница совпала с best для 2 cases. Дополнительные unrestricted CP-сертификаты: large #4, large #14, large #21, large #33, large #39, large #71, large #118, large #122, large #129, large #148, large #151, large #167, large #177, large #187, large #188. В этих моделях свободны все шесть эмиттеров и все времена, начальная поза фиксирована физикой, конец свободен, горизонт best−1, число принятий точное. INFEASIBLE исключает более короткую программу: любую такую программу можно дополнить выключением активных эмиттеров и holds. Объединение простых и CP-сертификатов охватывает 17 cases. CP OPTIMAL в задаче выполнимости сам по себе не доказывает минимальность найденной длины. UNKNOWN не является INFEASIBLE.

Все остальные утверждения о возможном усилении хорд, уменьшении периода или оптимальности общей суммы остаются гипотезами / NOT_PROVEN.

## Проверка и сохранность

```text
medium: CPP_INTERNAL_REPLAY + INDEPENDENT_PYTHON_VERIFY PASS, 210 cases, 5915 ticks
large: CPP_INTERNAL_REPLAY + INDEPENDENT_PYTHON_VERIFY PASS, 190 cases, 5092 ticks
enormous: CPP_INTERNAL_REPLAY + INDEPENDENT_PYTHON_VERIFY PASS, 140 cases, 4714 ticks
medium: SANDBOX_LOCAL_PASS 210 cases 5915 ticks
large: SANDBOX_LOCAL_PASS 190 cases 5092 ticks
enormous: SANDBOX_LOCAL_PASS 140 cases 4714 ticks
answer_level-6_2-medium.txt: SANDBOX_LOCAL_PASS, 210 cases, 5915 ticks
answer_level-6_3-large.txt: SANDBOX_LOCAL_PASS, 190 cases, 5092 ticks
answer_level-6_4-enormous.txt: SANDBOX_LOCAL_PASS, 140 cases, 4714 ticks
PROTECTED_FILE_BYTES_PASS 805 files; tracked worktree unchanged
FULL_VALIDATION_PASS 540 cases 15721 ticks; no commands after Kth acceptance
```

Дополнительно последний движок совпал с независимыми Python/JS на 22201 состояниях всех 540 cases, включая 12 seeded случайных продолжений на case. Root fixture: legacy 0 команд, fixed 1; оригинальный sandbox принял исправленную программу.

Исходный validate_l6_sandbox.cjs запущен побайтно неизмененным в experiments/validation_stage/. Более строгий адаптер дополнительно проверил отсутствие команд после K-го принятия. Checkpoints записываются атомарно; best заменяется только строгим улучшением после валидации. Запись полного набора сериализована per-dataset lock. Финальная сверка включает минимум всех сохраненных checkpoints. Near-miss и неуспешные/UNKNOWN попытки сохранены отдельно.

Ни один файл level-6/, прошлых экспериментов или исходных движков не изменен; байты всех 805 первоначальных файлов совпали. Git HEAD и ветка main не менялись. Commit, push, PR, submission и platform acceptance не выполнялись.

## Ограничения ресурсов и воспроизведение

У C++ заданы deadline, ограниченная ширина beam и пулы WIDTH×5, число хранимых альтернатив ограничено. Запуск измеряется отдельно; внешний IPC watchdog завершает только собственный процесс при превышении ms+15s. CP использует 2 workers, лимит времени и в актуальном exact_model лимит памяти 1024 MB. Старые ранние CP-запуски выполнялись до добавления этого memory ceiling. Нет запущенных фоновых оптимизаторов. Возобновление: использовать --indices/--seed для выбранных cases; best и banks не сбрасываются.

Все исходники находятся в engines/. cellfirst.exe соответствует восстановленному cellfirst_stage_b.cpp: SHA256 секции PE .text исходного и пересобранного бинарника совпал. Stage-A source восстановлен обратным применением поздних изменений; независимый code-hash исходного раннего бинарника не сохранен. Отдельные точные snapshots Stage C / library / full / discover сохранены вместе с бинарниками и SHA256. В текущем native.py поддерживаются оба выходных протокола.

Из корня репозитория (новый baseline prepare запрещает сброс существующего эксперимента):

```powershell
python training_l6_cellfirst/build.py cellfirst_discover.cpp
python training_l6_cellfirst/run_search.py --algorithms 0,1,2,3 --ms 250 --width 24 --follow 1 --tag repeat_pilot
python training_l6_cellfirst/run_assignment.py --datasets large --mode all --algorithms 7 --ms 250 --jobs 4 --tag repeat_assignment --seed 1000000
python training_l6_cellfirst/run_assignment.py --datasets enormous --mode all --algorithms 7 --ms 500 --jobs 4 --tag repeat_assignment --seed 1200000
python training_l6_cellfirst/run_constructive.py --engine cellfirst_discover.exe --algorithms 10 --ms 1800 --width 24 --tag repeat_fresh
python training_l6_cellfirst/repair_near.py --limit 24 --seconds 1.5 --datasets large,enormous --tag repeat_repair
python training_l6_cellfirst/exact_polish.py --limit 22 --seconds 6
python training_l6_cellfirst/test_native.py --engine cellfirst_discover.exe
node training_l6_cellfirst/compare_traces.cjs
python training_l6_cellfirst/geometry/analyze.py
python training_l6_cellfirst/validate_final.py
python training_l6_cellfirst/finalize.py
```

Ограниченный временем поиск зависит от машины и конкурирующей нагрузки. Повторный запуск поверх уже улучшенного best не обязан повторить прежний выигрыш. Для точного раннего baseline использовать сохраненные baseline/ и snapshots соответствующего движка в отдельной новой копии эксперимента. Пересчет итоговой проверки детерминирован по сохраненным ответам.

Полные данные: summary.json, results.csv, benchmark.csv, experiments/improvements_enriched.csv, experiments/ablation.json, experiments/exact_models/, geometry/lower_bounds.json и artifact_sha256.json. Ответы: три отдельных файла best/.
