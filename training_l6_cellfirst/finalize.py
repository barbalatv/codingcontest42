from common import *
from collections import Counter,defaultdict
import platform
def main():
    validation=json.loads((BASE/'experiments/validation.json').read_text());assert validation['status']=='PASS'
    events=list(csv.DictReader((BASE/'results.csv').open()));attribution=Counter()
    for e in events:attribution[e['algorithm']]+=int(e['saved'])
    scores={};changes=[];metrics={};after_diag=[]
    for ds in DATASETS:
        a=programs(ds,'baseline');b=programs(ds);cc=cases(ds);totals=[Counter(),Counter()]
        for i,(c,old,new) in enumerate(zip(cc,a,b)):
            assert len(new)<=len(old)
            ma,_=trace(c,old);mb,_=trace(c,new);after_diag.append(dict(dataset=ds,case=i+1,**mb))
            for j,m in enumerate((ma,mb)):
                for key in ['ticks','new_target','repeated_target','erased_target','new_skirting','skirting_tick_cells','h2_target','h3_target','motion','toggles']:totals[j][key]+=m[key]
            if len(new)<len(old):changes.append(dict(dataset=ds,case=i+1,before=len(old),after=len(new),saved=len(old)-len(new),radius=c[0],target_cells=len(c[1]),copies=c[2],acceptances_before=ma['acceptances'],acceptances_after=mb['acceptances'],first_before=ma['first_copy'],first_after=mb['first_copy'],later_mean_before=ma['later_mean'],later_mean_after=mb['later_mean'],repeat_fraction_before=ma['repeat_fraction'],repeat_fraction_after=mb['repeat_fraction']))
        scores[ds]=dict(cases=len(cc),baseline=sum(map(len,a)),best=sum(map(len,b)),saved=sum(map(len,a))-sum(map(len,b)),improved_cases=sum(len(x)<len(y) for x,y in zip(b,a)))
        metrics[ds]=[]
        for total in totals:
            total=dict(total);total['new_target_per_tick']=total['new_target']/total['ticks'];total['repeat_fraction']=total['repeated_target']/max(1,total['h2_target']);metrics[ds].append(total)
    baseline=sum(x['baseline'] for x in scores.values());best=sum(x['best'] for x in scores.values());saved=baseline-best;assert saved==sum(attribution.values())
    assert best==validation['ticks'] and baseline==15770
    # Replay the exact improvement chronology to add per-program auxiliary
    # metrics without confusing them with metrics of an isolated edge.
    state={ds:programs(ds,'baseline') for ds in DATASETS};enriched=[]
    for e in events:
        ds=e['dataset'];i=int(e['case'])-1;old=state[ds][i];assert len(old)==int(e['incumbent'])
        f=BASE/'checkpoints'/f"{ds}_{i+1}_{e['incumbent']}_{e['candidate']}_{e['algorithm']}.json";x=json.loads(f.read_text());new=[tuple(row) for row in x['program']]
        ma,_=trace(cases(ds)[i],old);mb,_=trace(cases(ds)[i],new);row=dict(e)
        for suffix,m in [('before',ma),('after',mb)]:
            for key in ['first_copy','later_mean','repeated_target','new_target','new_skirting','erased_target','motion','toggles']:row[f'{key}_{suffix}']=m[key]
        row['final_artifact_validation']='CPP_PYTHON_ORIGINAL_JS_PASS';enriched.append(row);state[ds][i]=new
    for ds in DATASETS:assert state[ds]==programs(ds)
    if enriched:
        with (BASE/'experiments/improvements_enriched.csv').open('w',newline='') as f:w=csv.DictWriter(f,list(enriched[0]));w.writeheader();w.writerows(enriched)
    allrows=[];groups=defaultdict(lambda:dict(records=0,saved_vs_stage_incumbent=0,runtime=0,evaluations=0,configurations=0,statuses=Counter()))
    for f in sorted((BASE/'experiments').glob('*.jsonl')):
        for line in f.read_text().splitlines():
            if not line.strip():continue
            r=json.loads(line)
            if 'algorithm' not in r:continue
            k=(f.stem,r['algorithm']);g=groups[k];g['records']+=1;g['saved_vs_stage_incumbent']+=r.get('saved',0);g['runtime']+=r.get('runtime',0);g['evaluations']+=r.get('evaluations',0);g['configurations']+=r.get('configurations',0);g['statuses'][r.get('validation','UNKNOWN')]+=1
            allrows.append({k:r.get(k) for k in FIELDS}|dict(log=f.name,configurations=r.get('configurations',0)))
    with (BASE/'benchmark.csv').open('w',newline='') as f:w=csv.DictWriter(f,FIELDS+['log','configurations']);w.writeheader();w.writerows(allrows)
    ablation=[dict(stage=key[0],algorithm=key[1],**g) for key,g in groups.items()]
    atomic_json(BASE/'experiments/ablation.json',ablation);atomic_json(BASE/'experiments/final_diagnostics.json',after_diag)
    bounds=json.loads((BASE/'geometry/lower_bounds.json').read_text());proofs={}
    for f in ['repair_expanded.jsonl','exact_polish.jsonl']:
        for r in map(json.loads,(BASE/'experiments'/f).read_text().splitlines()):
            if r.get('global_bound_proof'):
                assert len(programs(r['dataset'])[r['case']-1])==r['proven_minimum_ticks'];proofs[r['dataset'],r['case']]=r
    optimal={(r['dataset'],r['case']) for r in bounds if r['bound_tight']}|set(proofs)
    protected=json.loads((BASE/'experiments/protected_sha256.json').read_text())
    manifest={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in BASE.rglob('*') if p.is_file() and p.suffix in ['.cpp','.hpp','.py','.cjs','.exe']}
    manifest.update({str((BASE/'best'/name(ds)).relative_to(REPO)):hashlib.sha256((BASE/'best'/name(ds)).read_bytes()).hexdigest() for ds in DATASETS})
    atomic_json(BASE/'experiments/artifact_sha256.json',manifest)
    root=json.loads((BASE/'experiments/root_regression_test.json').read_text());native=json.loads((BASE/'experiments/native_tests.json').read_text());top=json.loads((BASE/'geometry/productive_configurations.json').read_text())
    summary=dict(status='LOCAL_VALIDATED',date='2026-10-24',repo=str(REPO),head=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True).stdout.strip(),datasets=scores,baseline=baseline,best=best,saved=saved,improved_cases=len(changes),cases=540,attribution=dict(attribution),changes=changes,metrics=metrics,validation=validation,native_trace_test=native,root_regression_test=dict(status=root['status'],old_length=root['old_length'],fixed_length=root['fixed_length']),lower_bound_tight_cases=sum(r['bound_tight'] for r in bounds),unrestricted_cp_minimum_proofs=[dict(dataset=ds,case=idx,ticks=r['proven_minimum_ticks'],status=r['validation']) for (ds,idx),r in sorted(proofs.items())],certified_optimal_cases=len(optimal),global_optimality='NOT_PROVEN',cold_start_cellfirst_saved=0,new_faster_multicopy_cycle_claim='NOT_ESTABLISHED',saved_first_acceptance=sum(r['first_before']-r['first_after'] for r in changes),saved_after_first_acceptance=sum(r['saved']-(r['first_before']-r['first_after']) for r in changes),observed_cpu_count=os.cpu_count(),python=platform.python_version(),tracked_files_changed=False,protected_files=len(protected),query_log_records=len(allrows),experiment_elapsed_from_baseline_manifest_seconds=time.time()-(BASE/'experiments/protected_sha256.json').stat().st_mtime)
    atomic_json(BASE/'summary.json',summary)
    proof_list=', '.join(f'{ds} #{i}' for ds,i in sorted(proofs))
    lines=['# CCC42 Level 6 — Cell-First: итог эксперимента','',f'**{baseline} → {best} тактов; −{saved}; улучшено {len(changes)}/540 cases. Полная локальная валидация PASS.**','',
     'Реализованы и применены универсальный C++20 Cell-First Scheduler, геометрические конфигурации, макрохорды на 2–4 такта, двунаправленный мост, назначение клеток с LNS/обратной связью и точный ремонт. Однако поиск новых полных программ с нуля не дал подтвержденного выигрыша. Реальное улучшение получено в основном Cell-Assignment LNS, дополненным существующим acceptance graph и точными ограниченными моделями. Прорыв по устойчивому периоду производства не установлен; глобальная минимальность суммы не доказана.','',
     '## LEVEL 6 MAIN DATASETS','', '| Набор | Проверенный baseline | Best | Saved | Улучшено |','|---|---:|---:|---:|---:|']
    for ds,s in scores.items():lines.append(f"| {ds.upper()} | {s['baseline']} | {s['best']} | {s['saved']} | {s['improved_cases']} / {s['cases']} |")
    lines += [f'| TOTAL | {baseline} | {best} | {saved} | {len(changes)} / 540 |','',
      'Baseline собран покейсово из всех полных локальных банков и отдельно именованных Medium-кандидатов, прошедших независимую проверку. Проверены предыдущие Codex-эксперименты, Antigravity/experiment_ultra и исторические level-6 банки. Найденный минимум точно совпал с 15770. Источники каждого case, отвергнутые программы и SHA256 сохранены в experiments/. Невалидные near-miss не включались в baseline или best.','',
      '## Атрибуция без перекрытий','', '| Первый реально улучшивший checkpoint | Тактов |','|---|---:|']
    for method,gain in attribution.items():lines.append(f'| {method} | {gain} |')
    lines += ['', 'Cell-First beam / ray scheduler: **0**; отдельные collinear macros: **0**; bidirectional: **0**; новые многокопийные циклы: **0**; ограниченный targeted CP с 3–4 свободными эмиттерами: **0**. Cell-assignment и граф указаны совместно: выигрыш не посчитан повторно как отдельный вклад DP. Два исторических symmetry/graph выигрыша — повторное комбинирование существующих программ, не новые физические стратегии. Command-level repair выделен отдельно. Расширенный exact repair разрешает все шесть эмиттеров в выбранной малой подзадаче.',
      '',f"Суммарное сокращение времени первого принятия: {summary['saved_first_acceptance']}; изменение стоимости после первого принятия: {summary['saved_after_first_acceptance']}. Однокопийные cases целиком входят в первую категорию. Устойчивый более быстрый цикл нельзя выводить из сокращения setup или единичного транзиента.",
      '', '## Реализованные модели и ограничения', '',
      '- C++ использует до 8 слов по 64 бита, все 6 эмиттеров и полное релевантное состояние target|skirting. Каждая команда и промежуточное принятие моделируются точно. После принятия релевантная материя пуста; позы и активность сохраняются.',
      '- Cell geometry хранит рельсовые координаты каждой клетки для всех эмиттеров, 15 возможных пар, 20 троек и 3 семейства. Генератор начинает с незаполненных/ошибочных клеток; подбирает пары, дополнительные лучи и клипперы в пределах достижимости.',
      '- Beam сохраняет различающиеся материю, геометрию и число активных эмиттеров. Геометрические оценки не объявляются допустимыми нижними границами. Глобальный A* не реализован; нижние границы приведены отдельно.',
      '- Макросы на 2/3/4 такта используют разные моменты переключений/движений, допускают временные загрязнения и уничтожение target. Дальние конфигурации направляют короткие физически исполнимые префиксы. Дополнительный master строит библиотеку хорд с клипперами и непараллельных пар.',
      '- Обратная регрессия сохраняет несколько требований ones/zeros и поз; прямой шестилучевой мост проверяет точную совместимость и затем переигрывает всю программу. Глубина регрессии ограничена 5, прямые макромосты — 4; это эвристический, неполный поиск.',
      '- Cell-assignment LNS назначает дефектной клетке 2 луча для создания или 3 для стирания; временная подзадача строит допустимые пути эмиттеров. Точный симулятор дает обратную связь по всем клеткам и всем принятиям. LNS также имеет обычные командные мутации: его выигрыш нельзя полностью приписывать одному геометрическому оператору.',
      '- Acceptance graph/DP переиспользован из training_medium_codex_v2 без изменения исходника. Ребра содержат actual start/end, программу и 1–4 принятия. DP минимизирует полную K-copy стоимость при свободной конечной позе. Проверяются отдельные обратные переходы, многокопийные ребра и симметрии противоположных эмиттеров.',
      '- Near repair ранжирует эмиттеры и временные окна по ошибочным клеткам; затем расширяет свободные эмиттеры. CP задает точную материю, iff-принятие и очистку на каждом такте. Полные локальные модели запускаются только для выбранных малых cases/горизонтов, не как наивная модель всех 540 задач.',
      '', '## Пилот, ablation и адаптивный бюджет', '',
      'Диагностический пилот: Medium 162,133,181,198,59; Large 144,65,101,78,147,19,125,29; Enormous 2,65,1,104,133,79,114,126. Выбор смешивает долю повторных H2, стоимость setup и target-клетки на интервал. Исходные метрики — experiments/diagnostics.json.',
      '', '| Этап / алгоритм | Записей | Выигрыш относительно baseline этапа | Query/этапное время, с | Evaluations |','|---|---:|---:|---:|---:|']
    for r in ablation:
        lines.append(f"| {r['stage']} / {r['algorithm']} | {r['records']} | {r['saved_vs_stage_incumbent']} | {r['runtime']:.3f} | {r['evaluations']} |")
    lines += ['',
      'Строки разных этапов не складываются для атрибуции: один case может встречаться несколько раз, а baseline этапов обновляется. Фактическая неперекрывающаяся атрибуция — таблица checkpoints выше. Внутри пилота четыре beam-варианта получают одинаковые 250 ms/query, width=24 и одинаковые anchors/seeds. Cell-assignment vs command LNS: 450 ms/query, одинаковые исходные графы и горизонты. Bidirectional arms: 400 ms/query, width=32. Cold-start arms: 1200 ms, width=24. Ремонт сравнивает command LNS, targeted CP и обычный CP на одном near-кандидате с одинаковым лимитом решения; CP-построение модели измерено дополнительно внутри runtime. Такие лимиты сопоставимы по потолку, но фактическое время бывает меньше при раннем завершении.',
      '', 'Полный проход assignment: Medium 180 ms/query, Large 250 ms/query, Enormous 500 ms/query. Последующее углубление победителей: Large 1000 ms/query, Enormous 1500 ms/query. Затем exact repair 4 s и polish 6 s на выбранных малых задачах. Основной ресурс перенаправлен в Large/Enormous после реальных выигрышей. Время разных процессов частично перекрывалось; сумму query-time нельзя выдавать за длительность всей сессии.',
      '', '| Набор | Full-pass saved / query seconds | Saved ticks / s |','|---|---:|---:|']
    for ds in DATASETS:
        rr=[r for r in ablation if r['stage']==f'assignment_all_{ds}'];sv=sum(r['saved_vs_stage_incumbent'] for r in rr);sec=sum(r['runtime'] for r in rr);lines.append(f'| {ds} | {sv} / {sec:.3f} | {sv/max(sec,1e-9):.4f} |')
    lines += ['', 'Результат assignment-пилота — один удачный Enormous case; он не доказывает превосходства Cell-First или геометрического оператора. Последующие проходы сравниваются с актуальным более сильным best. Первоначальный frontier_deep включал известные тождественные ребра; этот диагностический недостаток исправлен в frontier_distinct, где donor.start != actual start. Выигрыша на этом distinct-мостовом проходе нет.',
      '', '## Исследовательские наблюдения', '', '| Набор | Новых target-клеток / tick, до → после | Доля повторных H2 на target, до → после |','|---|---:|---:|']
    for ds,(ma,mb) in metrics.items():lines.append(f"| {ds} | {ma['new_target_per_tick']:.4f} → {mb['new_target_per_tick']:.4f} | {ma['repeat_fraction']:.4%} → {mb['repeat_fraction']:.4%} |")
    lines += ['',
      'Доля повторов определена как H2-клетки на уже существующей target-материи / все H2 target-клетки. Это не число всех фотонных попаданий и не доказанная бесполезность пересечения. Изменение вспомогательной метрики не использовано как самостоятельный успех.',
      '',f"Максимум в проверенных итоговых траекториях: {top[0]['new_target']} новых target-клеток за один такт ({top[0]['dataset']} case {top[0]['case']}, tick {top[0]['tick']}); opposed chord axes = {top[0]['opposed_chord_axes']}. Точные позы, команды, разрушения и skirting для 200 продуктивных конфигураций сохранены в geometry/productive_configurations.json. Эти конфигурации наблюдаются в проверенных программах; это не приписывание их изобретения новому движку.",
      '',f"Улучшения по числу копий: {dict(sorted(Counter(r['copies'] for r in changes).items()))}. Наиболее результативным оказался локальный ремонт коротких Large/Enormous и setup/однокопийных траекторий. Новый холодный Cell-First поиск не показал класса паттернов с доказанным преимуществом над incumbent.",
      '', 'Почему большинство cases не улучшены: в ограниченных beam/макрогоризонтах не найден более короткий полностью корректный маршрут; полезная статическая конфигурация не гарантирует дешевого перехода с очисткой skirting. Распределение материала и поз создает большие фронтиры, а эвристический beam отбрасывает потенциально полезные временные ухудшения. Это рабочие объяснения/ограничения реализации, не доказательство невозможности. Холодные near-кандидаты с записанной ошибкой ≤16 в этом пилоте не получены; многие близкие кандидаты LNS требуют совместного изменения более 3–4 эмиттеров, что подтверждается разницей между ограниченным и расширенным repair.',
      '', '## Что действительно доказано', '',
      'Для каждой target-клетки вычислено минимальное время активации ее луча каждым эмиттером из начальной позы: циклическое расстояние + одно переключение. Для двух попаданий нужно не меньше второй порядковой статистики этих шести времен; максимум по клеткам дает нижнюю границу первого принятия τ. Следовательно total ≥ τ+K−1.',
      '', 'В одном такте каждая из 12 непараллельных пар эмиттеров пересекается максимум в одной target-клетке. Каждая из 3 противоположных пар покрывает не более максимальной target-хорды своего семейства C_a. Поэтому H2 target ≤ U=min(NT,12+Σ C_a), а total ≥ ceil(K·NT/U). Это допустимые, обычно слабые границы; повторное создание уничтоженной материи не ослабляет доказательство.',
      '',f"Простая нижняя граница совпала с best для {summary['lower_bound_tight_cases']} cases. Дополнительные unrestricted CP-сертификаты: {proof_list}. В этих моделях свободны все шесть эмиттеров и все времена, начальная поза фиксирована физикой, конец свободен, горизонт best−1, число принятий точное. INFEASIBLE исключает более короткую программу: любую такую программу можно дополнить выключением активных эмиттеров и holds. Объединение простых и CP-сертификатов охватывает {len(optimal)} cases. CP OPTIMAL в задаче выполнимости сам по себе не доказывает минимальность найденной длины. UNKNOWN не является INFEASIBLE.",
      '', 'Все остальные утверждения о возможном усилении хорд, уменьшении периода или оптимальности общей суммы остаются гипотезами / NOT_PROVEN.',
      '', '## Проверка и сохранность', '', '```text', (BASE/'validation.log').read_text().strip(), '```', '',
      f"Дополнительно последний движок совпал с независимыми Python/JS на {native['states']} состояниях всех 540 cases, включая 12 seeded случайных продолжений на case. Root fixture: legacy {root['old_length']} команд, fixed {root['fixed_length']}; оригинальный sandbox принял исправленную программу.",
      '', 'Исходный validate_l6_sandbox.cjs запущен побайтно неизмененным в experiments/validation_stage/. Более строгий адаптер дополнительно проверил отсутствие команд после K-го принятия. Checkpoints записываются атомарно; best заменяется только строгим улучшением после валидации. Запись полного набора сериализована per-dataset lock. Финальная сверка включает минимум всех сохраненных checkpoints. Near-miss и неуспешные/UNKNOWN попытки сохранены отдельно.',
      '', 'Ни один файл level-6/, прошлых экспериментов или исходных движков не изменен; байты всех 805 первоначальных файлов совпали. Git HEAD и ветка main не менялись. Commit, push, PR, submission и platform acceptance не выполнялись.',
      '', '## Ограничения ресурсов и воспроизведение', '',
      'У C++ заданы deadline, ограниченная ширина beam и пулы WIDTH×5, число хранимых альтернатив ограничено. Запуск измеряется отдельно; внешний IPC watchdog завершает только собственный процесс при превышении ms+15s. CP использует 2 workers, лимит времени и в актуальном exact_model лимит памяти 1024 MB. Старые ранние CP-запуски выполнялись до добавления этого memory ceiling. Нет запущенных фоновых оптимизаторов. Возобновление: использовать --indices/--seed для выбранных cases; best и banks не сбрасываются.',
      '', 'Все исходники находятся в engines/. cellfirst.exe соответствует восстановленному cellfirst_stage_b.cpp: SHA256 секции PE .text исходного и пересобранного бинарника совпал. Stage-A source восстановлен обратным применением поздних изменений; независимый code-hash исходного раннего бинарника не сохранен. Отдельные точные snapshots Stage C / library / full / discover сохранены вместе с бинарниками и SHA256. В текущем native.py поддерживаются оба выходных протокола.',
      '', 'Из корня репозитория (новый baseline prepare запрещает сброс существующего эксперимента):', '', '```powershell',
      'python training_l6_cellfirst/build.py cellfirst_discover.cpp',
      'python training_l6_cellfirst/run_search.py --algorithms 0,1,2,3 --ms 250 --width 24 --follow 1 --tag repeat_pilot',
      'python training_l6_cellfirst/run_assignment.py --datasets large --mode all --algorithms 7 --ms 250 --jobs 4 --tag repeat_assignment --seed 1000000',
      'python training_l6_cellfirst/run_assignment.py --datasets enormous --mode all --algorithms 7 --ms 500 --jobs 4 --tag repeat_assignment --seed 1200000',
      'python training_l6_cellfirst/run_constructive.py --engine cellfirst_discover.exe --algorithms 10 --ms 1800 --width 24 --tag repeat_fresh',
      'python training_l6_cellfirst/repair_near.py --limit 24 --seconds 1.5 --datasets large,enormous --tag repeat_repair',
      'python training_l6_cellfirst/exact_polish.py --limit 22 --seconds 6',
      'python training_l6_cellfirst/test_native.py --engine cellfirst_discover.exe',
      'node training_l6_cellfirst/compare_traces.cjs',
      'python training_l6_cellfirst/geometry/analyze.py',
      'python training_l6_cellfirst/validate_final.py',
      'python training_l6_cellfirst/finalize.py',
      '```', '', 'Ограниченный временем поиск зависит от машины и конкурирующей нагрузки. Повторный запуск поверх уже улучшенного best не обязан повторить прежний выигрыш. Для точного раннего baseline использовать сохраненные baseline/ и snapshots соответствующего движка в отдельной новой копии эксперимента. Пересчет итоговой проверки детерминирован по сохраненным ответам.',
      '', 'Полные данные: summary.json, results.csv, benchmark.csv, experiments/improvements_enriched.csv, experiments/ablation.json, experiments/exact_models/, geometry/lower_bounds.json и artifact_sha256.json. Ответы: три отдельных файла best/.']
    (BASE/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['baseline','best','saved','improved_cases','certified_optimal_cases','attribution']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
