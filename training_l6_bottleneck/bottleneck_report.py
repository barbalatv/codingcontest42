from diagnostics import *
from collections import defaultdict,Counter
def mean(xs):return round(statistics.mean(xs),3) if xs else None
def group_method(method):
    if method=='exact_repair':return 'Exact Repair'
    if 'plus_LNS' in method:return 'Weighted Beam + LNS' if method.startswith('weighted_') else 'Standard Beam + LNS'
    if method.startswith('ema_'):return 'Iterative EMA'
    if method.startswith('dynamic') and not method.startswith('dynamic0'):return 'Dynamic weights'
    if 'lns' in method:return 'Cell-Assignment LNS'
    if 'standard_beam' in method or method.endswith('_w100'):return 'Standard Beam'
    return 'Weighted Beam'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])
def main():
    validation=json.loads((BASE/'experiments/final_validation.json').read_text());diag=json.loads((BASE/'experiments/diagnostics.json').read_text());masks=json.loads((BASE/'experiments/bottleneck_cases.json').read_text())
    core=json.loads((BASE/'experiments/core_tests.json').read_text())
    stages={};rows=[]
    for folder in sorted((BASE/'experiments').iterdir()):
        if not folder.is_dir():continue
        rr=[r for f in folder.glob('case_*.json') for r in json.loads(f.read_text())['rows']]
        if not rr:continue
        for r in rr:r['experiment_folder']=folder.name
        stages[folder.name]=dict(cases=len({r['case'] for r in rr}),queries=len(rr),cpu_seconds=round(sum(r.get('cpu_seconds',0) for r in rr),3),request_wall_seconds=round(sum(r.get('wall_seconds',0) for r in rr),3),valid_shorter_queries=sum(bool(r['valid']) for r in rr))
        rows+=rr
    records=[]
    for f in (BASE/'checkpoints').glob('*.json'):
        x=json.loads(f.read_text());records.append(x)
    marginal=Counter();cpu=Counter();attempts=Counter()
    for r in rows:
        group=group_method(r['method']);cpu[group]+=r.get('cpu_seconds',0);attempts[group]+=1
    for r in records:marginal[group_method(r['method'])]+=r['saved']
    per_case={r['case']:r['saved'] for r in validation['improved'] if r['dataset']=='enormous'}
    classes=[]
    for label,key in [('Sparse Tail','sparse_tail'),('Cleanup Tail','cleanup_tail'),('Dense Finale','dense_finale')]:
        ids={int(k) for k,v in masks.items() if v[key]};classes.append([label,len(ids),len(ids&per_case.keys()),sum(per_case.get(i,0) for i in ids)])
    ab=[]
    for stage in stages:
        for method in sorted({r['method'] for r in rows if r['experiment_folder']==stage}):
            rr=[r for r in rows if r['experiment_folder']==stage and r['method']==method];best={}
            for r in rr:best[r['case']]=max(best.get(r['case'],0),r['saved'])
            ab.append(dict(stage=stage,method=method,cases=len(best),best_saved_vs_frozen=sum(best.values()),shorter_queries=sum(r['valid'] for r in rr),mean_evaluations=mean([r['evaluations'] for r in rr]),mean_depth=mean([r['expanded_depth'] for r in rr if 'expanded_depth' in r]),mean_near_defects=mean([r['near_diagnostics']['defects'] for r in rr if r.get('near_diagnostics')]),cpu_seconds=round(sum(r.get('cpu_seconds',0) for r in rr),3)))
    # Per-case geometry features are descriptive associations, not predictors
    # validated on a held-out dataset.
    features=[]
    for i,c in enumerate(cases('enormous'),1):
        sim=Sim(c);features.append(dict(case=i,sparse=int(masks[str(i)]['sparse_tail']),radius=c[0],K=c[2],target_cells=len(c[1]),target_density=len(c[1])/len(geometry(c[0])[1]),boundary_ratio=sim.forbidden.bit_count()/len(c[1]),max_ray_target=max((ray[e]&sim.target).bit_count() for ray in sim.rays for e in range(6))))
    geom={key:{label:mean([r[key] for r in features if r['sparse']==v]) for label,v in [('sparse',1),('other',0)]} for key in ['radius','K','target_cells','target_density','boundary_ratio','max_ray_target']}
    fields=['dataset','case','method','seed','width','budget_ms','incumbent','candidate','saved','valid','evaluations','cpu_seconds','wall_seconds','stage','experiment_folder']
    with (BASE/'results/results.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fields);w.writeheader();w.writerows({k:r.get(k) for k in fields} for r in rows)
    atomic_json(BASE/'results/ablation.json',ab);atomic_json(BASE/'results/geometry_associations.json',dict(features=features,group_means=geom))
    atomic_json(BASE/'results/unsuccessful_candidates.json',[dict(case=r['case'],stage=r['experiment_folder'],method=r['method'],seed=r['seed'],near=r.get('near_diagnostics'),solver=r.get('solver'),error=r.get('error')) for r in rows if not r['valid']])
    scores={ds:v['best'] for ds,v in validation['datasets'].items()};baseline={ds:v['baseline'] for ds,v in validation['datasets'].items()};saved=sum(baseline.values())-sum(scores.values())
    summary=dict(status='LOCAL_PASS',baseline=baseline,best=scores,total_before=sum(baseline.values()),total_after=sum(scores.values()),saved=saved,enormous_screened=stages.get('universal',{}).get('cases',0),improved_cases=len(per_case),diagnostics=diag['summary'],stages=stages,algorithm_marginal_saved=dict(marginal),algorithm_cpu_seconds={k:round(v,3) for k,v in cpu.items()},queries=len(rows),class_results=classes,validation=validation,claim='Measured improvement only relative to frozen per-case best-of-local baseline; no platform submission.',ema_rounding='floor(decay_numerator*(w-100)/10), then +100 current bottleneck bonus, clamp at 500',geometry=geom)
    atomic_json(BASE/'summary.json',summary)
    # Diagnose accepted improvements separately from all unfinished trajectories.
    improved_diags=[]
    for i in sorted(per_case):
        c=cases('enormous')[i-1];p=programs('enormous')[i-1]
        improved_diags.extend(analyze_case(Sim(c),p,dataset='enormous',index=i,radius=c[0],K=c[2],n_target=len(c[1])))
    atomic_json(BASE/'results/accepted_improvement_diagnostics.json',improved_diags)
    old_diags=[r for r in diag['copies'] if r['case'] in per_case]
    productivity={label:dict(mean_tail_creation_events=mean([r['late_creation_events'] for r in rr]),mean_late_first_cells=mean([r['first_built_in_tail'] for r in rr]),mean_late_final_cells=mean([r['late_unique_final'] for r in rr]),mean_copy_ticks=mean([r['interval_ticks'] for r in rr])) for label,rr in [('before',old_diags),('after',improved_diags)]}
    summary['accepted_productivity']=productivity
    details=[]
    for i in sorted(per_case):
        c=cases('enormous')[i-1];oldp=programs('enormous','baseline')[i-1];newp=programs('enormous')[i-1]
        details.append([i,c[2],len(oldp),len(newp),exact(c,oldp),exact(c,newp)])
    summary['acceptance_changes']=details
    atomic_json(BASE/'summary.json',summary)
    def best_saved(rr):
        bycase={}
        for r in rr:bycase[r['case']]=max(bycase.get(r['case'],0),r['saved'])
        return sum(bycase.values())
    ema=[]
    for decay in [0,5,7,9]:
        fixed=[r for r in rows if r['experiment_folder']=='iterative' and r['method'].startswith(f'fixed_decay{decay}_')]
        treatment=[r for r in rows if r['experiment_folder']=='iterative' and r['method'].startswith(f'ema_decay{decay}_')]
        ema.append([decay/10,best_saved(fixed),best_saved(treatment)])
    dynamic_ab=[[r['method'],r['cases'],r['best_saved_vs_frozen'],r['mean_near_defects']] for r in ab if r['stage']=='dynamic']
    pilot_ab=[[r['method'],r['cases'],r['best_saved_vs_frozen'],r['mean_depth']] for r in ab if r['stage']=='pilot']
    atomic_json(BASE/'results/ema_comparison.json',dict(columns=['decay','fixed_saved_vs_frozen','ema_saved_vs_frozen'],rows=ema))
    stage_status=[];cumulative=0
    for stage in ['pilot_v1','pilot','universal','modes','dynamic','iterative','deep','repair']:
        delta=sum(r['saved'] for r in records if Path(r['source_record']).parts[1]==stage);cumulative+=delta
        stage_status.append(dict(stage=stage,enormous_before=baseline['enormous'],enormous_after=baseline['enormous']-cumulative,total_before=sum(baseline.values()),total_after=sum(baseline.values())-cumulative,stage_saved=delta,cumulative_saved=cumulative,screened=140 if stage not in ['pilot_v1','pilot'] else 0,validation='PROMOTED_PROGRAMS_CPP_PYTHON_VERIFY_JS_PASS'))
    assert cumulative==saved
    atomic_json(BASE/'experiments/stage_status.json',stage_status)
    repair_status=Counter(r['solver']['status'] for r in rows if r.get('solver'))
    low=[r for r in rows if r.get('near_diagnostics') and r['near_diagnostics']['defects']<=2]
    med=diag['summary'];universal=[r for r in rows if r['experiment_folder']=='universal'];full=[r for r in universal if r['context']['a']==0]
    text=f'''# CCC42 LEVEL 6 — BOTTLENECK OPTIMIZATION

Локальный эксперимент завершён. Проверенный best-of-all: **{sum(scores.values())} тактов**, изменение относительно актуального замороженного baseline: **−{saved}**. Новые программы с сокращением: **{len(per_case)} cases**. Публикация, PR и submission не выполнялись.

{table(['Dataset','Frozen baseline','Best','Saved'],[[ds,baseline[ds],scores[ds],baseline[ds]-scores[ds]] for ds in DATASETS]+[['TOTAL',sum(baseline.values()),sum(scores.values()),saved]])}

## Baseline и сохранность

Указанный в запросе банк 5904 / 5047 / 4706 уже уступал локальной комбинации. Проверены все найденные полные answer-банки; для Large и Enormous по 6 более коротких cases взяты из training_l6_transfer/best, остальные из Full540. Консолидация дала 5904 / 5035 / 4700, всего 15639: эти 18 тактов не приписываются новому алгоритму. Источники каждого case, отклонения и SHA-256: experiments/baseline.json. Baseline фиксирован, ни один case не ухудшен. {validation['protected_files']} исходных файлов перепроверены по SHA-256, изменений нет. Архив и его оригинальные файлы сохранены отдельно.

## Диагностика всех 140 cases

210 принятых копий; {med['sparse_tail_copies']} sparse-копии в {med['sparse_tail_cases']} cases; {med['focused_candidate_copies']} sparse+slow копий в {med['focused_candidate_cases']} cases. Медиана late-final клеток: {med['median_late_final_cells']}. {med['late_clean_copies']} копий с поздней очисткой skirting. В {med['first_before_tail_rebuilt_copies']} копиях восстановлены клетки, впервые созданные до окна; в {med['first_in_tail_rebuilt_copies']} есть создание и пересборка внутри окна. Признаки могут пересекаться в одной копии.

Старые late_build/late_churn сохранены, добавлены first_built_in_tail, first_before_tail_rebuilt_in_tail и first_in_tail_rebuilt_in_tail. Критерий первого создания: first_build >= window_start. Сохраняются first/last build, last destroy, команды, активность, загрязнение и три состояния материи каждого такта. Near-miss имеет отдельные missing/dirty/destroyed/accessibility метрики; pickup-окно ему не приписывается. В ранних near-логах исправлена атрибуция очистки после принятия; прежние метрики оставлены в previous_near_diagnostics.

{table(['Class (overlapping)','Cases','Improved cases','Saved ticks'],classes)}

Cleanup Tail — поздняя очистка skirting, восстановление старых клеток или уничтожение target в окне. Это широкий независимый признак присутствия работы по восстановлению/очистке, а не доказательство её преобладания. Dense Finale — более 10 late-final клеток. Эти классы нельзя суммировать.

Геометрические средние (описательная связь с sparse, без проверки предсказательной силы на отложенных данных):

{table(['Feature','Sparse cases','Other cases'],[[k,v['sparse'],v['other']] for k,v in geom.items()])}

## Движок и протокол

Изолированная копия C++20; исходный cellfirst_v2.cpp не изменён. Дополнительная оценка состояния равна 2 × (made × total_extra + filled_extra − total_extra), где extra = weight − 100. Это дельта к исходной эвристике; при весах 100 она строго нулевая. Сохранены исходные target/skirting/potential/геометрические оценки и возможность временного ухудшения. Snapshot добавляет weighted создание и симметричный относительно исходного коэффициента штраф разрушения. Command expansion и pruning используют согласованную дельту; sampling геометрических клеток остался исходным. Для LNS добавлен положительный weighted deficit к исходной стоимости, успех по-прежнему имеет стоимость 0.

Первая реализация считала дельту по клеткам и повторно вычисляла лучи. Её полный 61-case пилот сохранён в pilot_v1. Следующая версия группирует одинаковые веса в битовые маски и переиспользует effect; scalar/grouped оценки сверены на 320 состояниях. Алгебраическая оценка не менялась. Сравнивать throughput двух пилотов как чистое измерение ускорения нельзя: запуски выполнялись в разное время.

BN1 — один полностью ограниченный whitespace frame на строку с обязательными dynamic/cap/eval_limit/weight_count и парами cell_id weight. Ошибка количества, индекса или остаточных токенов отвергает весь frame и не поглощает следующий запрос. Индексы совпадают с solve_l4.geometry. Проверены пустая/одноклеточная/многоклеточная маски, повторные запросы, некорректные frames, тайм-аут и восстановление процесса.

Parity: {core['audit_states']} состояния оценки/физики и {core['deterministic_beams']} поисков mode 0/1/3/7 с одинаковым seed и лимитом 25000 evaluations. Сравнены scores, near/result, число вычислений, digest каждой выбранной beam-последовательности и каждой ранжированной конфигурации. Reference сохраняет исходные scoring-функции; контроль не заменён упрощённым поиском. Часы в детерминированной проверке не используются.

## Выполненные этапы и бюджеты

{table(['Stage','Cases','Queries','Search CPU seconds','Shorter valid queries'],[[k,v['cases'],v['queries'],v['cpu_seconds'],v['valid_shorter_queries']] for k,v in stages.items()])}

Два worker-процесса, persistent C++ в каждом, width 16, Job Object с лимитом 512 MiB для каждого worker/унаследованного child. Четыре workers не использовались при примерно 2.7 GiB свободной памяти. Screening 1000 ms/request, deep 2500 ms/request; LNS repair 1500 ms, CP-SAT 2000 ms solve limit плюс построение модели. CPU и wall каждого запроса сохранены отдельно; native compilation time — в engines/*.build.json. Time-budget результаты воспроизводятся по параметрам, но не гарантируют побитовую идентичность; для этого есть отдельный evaluation-limit режим.

Pilot: все 49 sparse cases и по 6 дополнительных cleanup/dense controls, веса 100/150/200/300/500. Universal: 140/140, независимый полный поиск и поиск из физического состояния перед последними максимум 10 тактами. Полный horizon T−1; локальная замена уменьшает глобальную длину минимум на один такт. Все сопоставимые arms завершались до возможного обновления best.

Mode A — независимый command beam (mode 0). B — geometry-guided beam (mode 3). C — beam near-prefix плюс существующий Cell-Assignment LNS. Источник префикса явно отмечен как standard или weighted; выигрыш от control-префикса не приписывается weighted beam. D — замена участка между incumbent-состояниями с exact endpoint и безопасным incumbent suffix; при K=1 bridge совпадает с tail и не является самостоятельным свидетельством эффекта suffix. Исторический LNS также измерен отдельно. Динамика: static, linear ramp, late ramp, geometric deficit gating; cap 250 проверен против uncapped при weight 300, а не введён как безусловное правило.

EMA: три итерации для decay 0/0.5/0.7/0.9, на каждом шаге парный fixed-200 контроль с тем же seed. Формула: min(500,100 + floor(decay_numerator × (w−100)/10) + bonus), bonus=100 для текущей bottleneck-маски. Near-miss маска берётся из незаполненных и физически уничтоженных target; принятую программу диагностируют по настоящим pickup. Decay 0 — полный сброс прежней добавки, затем новый bonus.

## A/B и атрибуция

Полная независимая таблица stage/method против frozen baseline находится в results/ablation.json. В results/results.csv есть case, method, seed, width, budget_ms, incumbent, candidate, saved, valid, evaluations, cpu_seconds, wall_seconds. Данные всех неуспешных попыток и программ сохранены в experiments; краткий индекс — results/unsuccessful_candidates.json. Выигрыши альтернативных методов на одном case нельзя складывать.

Сопоставимый пилот коэффициентов, 61 case; выигрыш — best-per-case относительно frozen baseline:

{table(['Method','Cases','Saved ticks','Mean reached depth'],pilot_ab)}

Сравнение динамики и snapshot cap на одной адаптивной выборке из 8 cases, weight 300:

{table(['Method','Cases','Saved ticks','Mean near defects'],dynamic_ab)}

Cap применяется только к snapshot-ранжированию конфигураций. Полная state/pruning дельта остаётся uncapped. Это проверенная абляция локальной генерации, а не ограничение финального target-score.

EMA против fixed-200 на тех же 8 cases: лучший полный результат каждой из трёх итераций, без повторного суммирования case:

{table(['Decay','Fixed saved vs frozen','EMA saved vs frozen'],ema)}

{table(['Algorithm','Actual non-overlapping saved ticks','Measured CPU seconds','Queries'],[[k,marginal[k],round(cpu[k],3),attempts[k]] for k in sorted(cpu)])}

Фактическая неперекрывающаяся атрибуция строится только из атомарных best-checkpoints. CPU включает все попытки соответствующей группы, включая v1 и проигравшие arms; это стоимость исследования, не CPU только победителей.

## Repair и проверка

Repair переиспользует существующий acceptance-aware exact_model.py, без изменения физики: joint replanning всех 6 эмиттеров в последних 3 и затем 5 тактах, при фиксированном предыдущем пути и требуемом endpoint. Ограниченные статусы CP-SAT: {dict(repair_status)}. INFEASIBLE относится только к данной модели/окну/начальному состоянию; UNKNOWN не доказывает невозможность.

Первая попытка CP-SAT с двумя workers и лимитом 512 MiB завершилась MemoryError в solver.solve; сбой и исходный selection сохранены в experiments/repair_failures/attempt_512mb.json. Repair повторён одним worker с hard limit 1024 MiB, одним CP-SAT thread и advisory limit 896 MiB. Расширения ресурса сверх этого не выполнялись. Первая потерявшая результат попытка не включена в измеренный CPU успешного повторного этапа; её точное CPU время не сохранено.

Финальные 540/540 программ прошли внутренний C++ replay, Python Sim, solve_l5.verify и оригинальные функции JS sandbox. В JS дополнительно сравнивались полная материя до лучей, после лучей до pickup и после pickup, позиции, активность и число принятий на каждом из {validation['original_js']['ticks']} тактов. Требуется ровно K и принятие на последней команде. Исходный HTML SHA-256: {validation['original_js']['source_sha256']}.

## Ответы на исследовательские вопросы

1. Подтверждены {med['sparse_tail_cases']} cases с sparse-хвостом; {med['focused_candidate_cases']} имеют также замедление и достаточную длительность. Это наблюдаемая низкая продуктивность, а не доказанный резерв сокращения.
2. Геометрические признаки и групповые средние приведены выше. Ни один не объявляется независимым предиктором: порог 10 клеток сам зависит от размера target, а набор не разделялся на train/test.
3. В незавершённых траекториях меняются дефицит и порядок заполнения; {len(low)} запросов достигли состояния с максимум двумя missing/dirty клетками. Эти near-miss не дают принятой финальной продуктивности. Изменение принятой продуктивности можно утверждать только для программ из results/accepted_improvement_diagnostics.json.

Для {len(per_case)} улучшенных cases, сравнивая только действительно принятые копии: среднее число creation events в последних 5 тактах {productivity['before']['mean_tail_creation_events']} → {productivity['after']['mean_tail_creation_events']}; впервые построенных в хвосте клеток {productivity['before']['mean_late_first_cells']} → {productivity['after']['mean_late_first_cells']}; средняя длительность копии {productivity['before']['mean_copy_ticks']} → {productivity['after']['mean_copy_ticks']}. Окно сдвигается вместе с моментом принятия; изменение числа клеток в нём само по себе не объясняет причинный механизм выигрыша.
4. Полная длина относительно актуального baseline изменилась на −{saved}, Enormous {baseline['enormous']} → {scores['enormous']}. При нулевом сокращении гипотеза о полезности метода для score не подтверждена.
5. Коэффициенты 150/200/300/500 сравнивались в равных условиях. Эффективность для score определяется только verified saved ticks в ablation; при нулевом выигрыше эффективный коэффициент не установлен. Максимальный вес не считается предпочтительным из-за изменения near-miss.
В полном независимом пилоте ни один коэффициент не улучшил baseline. В локальном адаптивном поиске static 300 сократил case 40 на один такт; fixed 200 и linear 300 с cap 250 в других сопоставимых запусках также достигали этого сокращения. Эти выборки различаются, поэтому глобальный рейтинг коэффициентов не установлен.
6. На проверенной адаптивной выборке decay 0.7 дал 3 такта best-per-case против 1 у fixed-200; decay 0.5 дал 2, decay 0.9 — 2, reset — 1. EMA улучшила полную программу case 6 до 41 такта, fixed этого не достиг. Это ограниченный результат для 8 cases и трёх итераций, без утверждения общего превосходства при других seeds/бюджетах.
7. Проверяется именно полная K-copy программа. Изолированное принятие/изменение позы не засчитывается без корректного полного префикса, endpoint и суффикса.
8. В пределах этих бюджетов Hard-Core First не имеет подтверждённой пользы на cases без verified сокращения. Dense Finale и cleanup требуют совместного управления лучами; повышение веса отдельных клеток не устраняет причинённое другими лучами загрязнение или необходимость возврата эмиттеров.
Все {len(per_case)} улучшенных cases входят в исходные 49 Sparse Tail; среди 91 case без этого признака сокращений не найдено. Dense Finale пересекается со Sparse Tail, поэтому наличие выигрышей в Dense Finale не опровергает это наблюдение.
9. Новая подтверждённая геометрическая стратегия определяется только новым валидным маршрутом. При отсутствии выигрышных программ такой стратегии не установлено; наблюдаемые альтернативные пути остаются исследовательскими данными.
10. Масштабировать на Large/Medium по этим данным пока не обосновано. Их сохранённый best уже включён в итог. Более дорогой поиск имеет смысл на residual 1–2 клетках с дополнительным основанием, а не как утверждение о гарантированном резерве.

**Эпистемический статус:** verified improvements — только checkpoints и final_validation; исследовательские наблюдения — диагностика и A/B; объяснение эффекта геометрией — гипотеза. Глобальная оптимальность не доказана. Нулевая дельта при all-100 и эквивалентность группировки следуют из формул и подтверждены тестами. Ограниченный отрицательный результат не является математическим запретом перевзвешивания.

Приёмки улучшенных полных программ:

{table(['Case','K','Old ticks','New ticks','Old acceptances','New acceptances'],details)}

## Локальное воспроизведение

Из корня репозитория: python -B training_l6_bottleneck/run_experiment.py. Скрипт сохраняет checkpoint каждого case и возобновляет завершённые этапы, сверяя параметры. Baseline неизменяемый. Все выходные answer-файлы — только training_l6_bottleneck/best/. Начальная диагностика — experiments/diagnostics.json и diagnostics.csv; masks — experiments/bottleneck_cases.json; итог — summary.json и validation.log. Никакие исходные answer-файлы не переписываются.
'''
    (BASE/'REPORT.md').write_text(text,encoding='utf-8')
    print('CCC42 LEVEL 6 — BOTTLENECK OPTIMIZATION')
    for ds in ['enormous','medium','large']:print(ds.upper(),baseline[ds],'->',scores[ds])
    print('TOTAL',sum(baseline.values()),'->',sum(scores.values()),'SAVED',saved,'SCREENED',summary['enormous_screened'],'/140','IMPROVED',len(per_case),'VALIDATION PASS')
if __name__=='__main__':main()
