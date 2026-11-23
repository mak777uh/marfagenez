# -*- coding: utf-8 -*-
import json, pathlib
D = 'bio.information_error'
C = []


def add(**kw):
    base = {'atom': '', 'statement': '', 'domain': D, 'kind': '', 'mechanism': '',
            'formula': '', 'symbols': {}, 'conditions': [], 'works': [],
            'confidence': 'medium', 'locator_status': 'verified', 'tags': [], 'notes': ''}
    base.update(kw)
    C.append(base)


add(atom='DIP23-0001',
    statement='В репликативно стареющих дрожжах уровень и потенциальная ёмкость 26S протеасомы сохранены, но деградация цитозольного субстрата UPS в клетке нарушена; конститутивное повышение активности диз-aggregase Hsp104 восстанавливает деградацию этого субстрата, не повышая уровень протеасом.',
    kind='measurement',
    mechanism='деградацию лимитирует не каталитическая ёмкость протеасомы, а доступность субстрата, запертого в агрегатах: разрушение агрегата возвращает субстрат машине, и только тогда срабатывает уже имеющаяся ёмкость',
    conditions=['Saccharomyces cerevisiae', 'репликативное старение', 'ΔssCPY* как цитозольный субстрат UPS',
                'интеграция pGPD-HSP104 в геном (конститутивная диз-aggregase активность)',
                'уровень и потенциальная ёмкость протеасом не изменялись'],
    works=[{'doi': '10.18632/aging.100613', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'this elevated disaggregation restored degradation of a 26S proteasome substrate in aged cells without elevating proteasome levels'}],
    tags=['availability', 'disaggregase', 'proteasome-capacity', 'yeast', 'aging', 'Hsp104'],
    notes='В аннотации же: «the level and potential capacity of the 26S proteasome is maintained in replicatively aged cells, the UPS is not functioning properly in vivo» (в аннотации OpenAlex слиплось «properlyin» — дефект склейки инвертированного индекса, не цитата). Самая прямая из найденных формулировок «ёмкость есть, доступности нет».')

add(atom='DIP23-0002',
    statement='При снижении уровня Hsp70 (Ssa1/Ssa2) убиквитинилированные субстраты деградации не разрушаются, а секвестируются в Hsp42-положительные детергент-нерастворимые тельца; предотвращение убиквитинилирования субстрата отменяет эту секвестрацию.',
    kind='condition',
    mechanism='решение «деградация или секвестрация» принимается после убиквитинилирования и на уровне Hsp70: мало Hsp70 — переключатель уходит в сторону недоступности, хотя метка деградации уже стоит',
    conditions=['Saccharomyces cerevisiae', 'несколько слабо misfolded субстратов деградации', 'деплеция Ssa1/Ssa2',
                'Hsp40 Sis1 обязателен для убиквитинилирования субстрата', 'Hsp42-положительные включения'],
    works=[{'doi': '10.1091/mbc.e13-01-0010', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'in Ssa1/Ssa2-depleted cells, ubiquitylated substrates are sequestered into detergent-insoluble, Hsp42-positive inclusion bodies'}],
    tags=['saturation', 'Hsp70', 'sequestration', 'switch', 'ubiquitin', 'yeast'],
    notes='Ключевое для домена: насыщение происходит не по протеасоме, а по шаперону-переносчику; убиквитиновая метка сама по себе не гарантирует деградацию. Возрастное падение Hsp70 авторы прямо связывают с убиквитин-зависимой секвестрацией.')

add(atom='DIP23-0003',
    statement='Повышение клеточного уровня Hsp70 SSA1 приводит к полному удалению включений misfolded протеинкиназ протеасомой и ускоряет их оборот.',
    kind='measurement',
    mechanism='доступность клиента к протеасоме лимитирована количеством шаперона-переносчика, поэтому добавление шаперона, а не протеасомы, снимает ограничение',
    conditions=['Saccharomyces cerevisiae', 'misfolded протеинкиназы', 'ингибирование SSA1 или Hsp90, тепловой стресс',
                'сверхэкспрессия SSA1'],
    works=[{'doi': '10.1091/mbc.e14-08-1262', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'Up-regulation of SSA1 results in complete removal of these inclusions by the proteasome'}],
    tags=['availability', 'Hsp70', 'inclusions', 'clearance', 'yeast'],
    notes='Положительный контроль к «потолку доступности»: здесь добавление компонента доступности ускоряет очистку. Включения бывают разного типа (нерастворимые при ингибировании SSA1, растворимые при ингибировании Hsp90, стресс-фокусы при нагреве) — доступность зависит от компартмента, в котором оказался клиент.')

add(atom='DIP23-0004',
    statement='Маршрут очистки TDP-43 определяется его состоянием: растворимый TDP-43 деградируется преимущественно UPS, а клиренс агрегированного TDP-43 требует аутофагии.',
    kind='condition',
    mechanism='доступность задаётся фазовым состоянием субстрата: растворимая молекула доходит до протеасомы, агрегат — нет, и его приходится забирать аутофагией',
    conditions=['культивируемые клетки, модели ALS/FTD', 'ингибиторы UPS и аутофагии', 'TDP-43 дикого типа и ALS-мутанты',
                'макроагрегаты, воспроизводящие признаки агрегатов пациентов'],
    works=[{'doi': '10.1242/jcs.140087', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'soluble TDP-43 is degraded primarily by the UPS, whereas the clearance of aggregated TDP-43 requires autophagy'}],
    tags=['availability', 'phase-state', 'TDP-43', 'UPS', 'autophagy', 'split-routes'],
    notes='В аннотации также: макроагрегаты обратимы, когда работают оба пути, и их клиренс идёт через аутофагическое удаление олигомерного TDP-43. Доли в аннотации не приведены — ячейка-условие, не число.')

add(atom='DIP23-0005',
    statement='Аутофагический клиренс агресом не универсален: агресомы из AIMP2 (p38) или мутантного десмина устойчивы к аутофагии и не рекрутируют ключевые компоненты аутофагически-лизосомальной системы, тогда как агресомы из мутантного хантингтина, тау или синуклеина с синфилином-1 клиренсуются.',
    kind='condition',
    mechanism='доступность включения машинерии задаётся его составом: «неизбирательный» путь аутофагии на деле избирателен к составу агрегата, и смена состава переводит устойчивое включение в клиренсуемое',
    conditions=['культивируемые клетки', 'эктопическая экспрессия aggregation-prone белков', 'агресомы разного белкового состава',
                'сравнение чувствительных и устойчивых включений'],
    works=[{'doi': '10.1093/hmg/ddn157', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'those produced in AIMP2 (p38)- or mutant desmin-expressing cells are apparently resistant to autophagic clearance'}],
    tags=['ceiling', 'aggresome', 'autophagy', 'composition', 'selectivity'],
    notes='Это и есть случай «потолок доступности»: усиление аутофагии не помогает, пока состав включения не рекрутирует лизосомальную машинерию. Авторы меняли состав и делали устойчивые агресомы восприимчивыми — то есть доступность здесь восстановима изменением субстрата, а не усилением пути.')

add(atom='DIP23-0006',
    statement='Белки, образующие агресомы, имеют ускоренную скорость оборота, и этот оборот замедляется при ингибировании образования агресом.',
    kind='measurement',
    mechanism='агресома работает как центр рекрутирования компонентов деградации и повышает доступность белка, а не только изолирует его',
    conditions=['культивируемые клетки', 'мутантный андрогеновый рецептор (спинобульбарная мышечная атрофия)',
                'молекулярные и фармакологические вмешательства в образование агресом',
                'связь агресом с лизосомальными структурами'],
    works=[{'doi': '10.1093/hmg/ddg074', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'Aggresome-forming proteins were found to have an accelerated rate of turnover, and this turnover was slowed by inhibition of aggresome formation'}],
    tags=['aggresome', 'turnover-rate', 'availability', 'positive-control', 'polyQ'],
    notes='Относительная величина (ускоренный/замедленный оборот), а не абсолютная константа: чисел в аннотации нет. Контрпример к «любая агрегация уменьшает доступность»: правильно организованное включение доступность повышает.')

add(atom='DIP23-0007',
    statement='Арсенит-индуцированные агрегаты очищаются в основном UPS, но связывание шаперонов с такими агрегатами нарушено при неизменной активности Hsp104 и Hsp70: доступность задаётся структурой агрегата, а не активностью машины.',
    kind='measurement',
    mechanism='химическая модификация (арсенит по цистеинам) меняет структуру агрегата так, что машинария работает нормально, но не может связать субстрат',
    conditions=['Saccharomyces cerevisiae', 'арсенит-стресс in vivo',
                'очищенные компоненты дрожжевой диз-aggregase машины in vitro', 'тест с cysteine-free вариантом субстрата'],
    works=[{'doi': '10.1016/j.jbc.2022.102680', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'Hsp104 and Hsp70 chaperone activity was unaffected by arsenite, suggesting that this metalloid influences aggregate structure, making them less accessible for chaperone-mediated disaggregation'}],
    tags=['ceiling', 'availability', 'aggregate-structure', 'Hsp104', 'Hsp70', 'arsenite'],
    notes='Второй случай «потолка доступности»: активность машины не падает, падает связывание. Вклады путей по аннотации: UPS — главный, аутофагия-вакуоль и шаперонный рефолдинг — менее выражены.')

add(atom='DIP23-0008',
    statement='Для Aβ измерены константа скорости деградации катепсином B и константа равновесия связывания цистатина C с Aβ; отношение приближённых полувремён деградации и агрегации позволяет при данных концентрациях Aβ, CatB и CysC решить, что победит — агрегация или деградация.',
    kind='measurement',
    formula='t(1/2,deg) / t(1/2,agg) — схематическая запись отношения, названного в аннотации',
    symbols={'t(1/2,deg)': 'приближённое полувремя деградации Aβ катепсином B',
             't(1/2,agg)': 'приближённое полувремя агрегации Aβ',
             'k(deg,CatB)': 'константа скорости деградации Aβ катепсином B (измерена)',
             'K(eq,CysC-Aβ)': 'константа равновесия связывания цистатина C с Aβ (измерена)'},
    mechanism='конкуренция деградации и агрегации за один и тот же мономер: удерживающее связывание (CysC-Aβ) одновременно снижает доступность субстрата протеазе и тормозит агрегацию, поэтому знак эффекта зависит от отношения скоростей',
    conditions=['in vitro, очищенные Aβ, катепсин B, цистатин C', 'измеренная кинетика агрегации Aβ без CatB и CysC',
                'математическая модель материальных балансов и кинетических уравнений',
                'предсказание проверено при разных концентрациях CatB и CysC'],
    works=[{'doi': '10.1074/jbc.m117.811448', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'The rate constant for Aβ degradation by CatB and the equilibrium constant for binding of CysC to Aβ were determined'}],
    tags=['kinetics', 'binding-constant', 'half-time-ratio', 'cathepsin-B', 'cystatin-C', 'amyloid-beta'],
    notes='Формула намеренно не выписана как алгебра: аннотация называет «approximate expressions for the half-times of degradation and aggregation» и говорит, что используется их отношение, но самих выражений не приводит. Числовые значения констант в аннотации не даны — нужен полный текст. Единственная найденная работа, где константа удержания агрегационного субстрата измерена вместе с константой его деградации.')

add(atom='DIP23-0009',
    statement='UPS и молекулярные шапероны конкурируют за один и тот же денатурированный белок, и судьба белка определяется относительными активностями этих путей; ко-шаперон CHIP с E3-активностью задаёт баланс между деградацией и рефолдингом.',
    kind='mechanism',
    mechanism='конкуренция за связывание субстрата: повышенная активность UPS подавляет рефолдинг, повышенная шаперонная активность подавляет деградацию, поэтому доля деградированного есть функция отношения активностей',
    conditions=['денатурированные белки in vitro и в клеточных моделях', 'CHIP, шапероны, изопептидазы как регуляторы',
                'сравнение повышенной активности UPS и повышенной шаперонной активности'],
    works=[{'doi': '10.1096/fj.05-5080fje', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'the UPP and molecular chaperones work in a competitive manner and that the fates of denatured proteins are determined by the relative activities'}],
    tags=['competition', 'partition', 'CHIP', 'chaperones', 'UPS', 'triage'],
    notes='Механизм «доли доступного деградации», но без числа: ни констант, ни долей в аннотации нет. Основание для формулы доли, калибровать по работам с числами (DIP23-0008).')

add(atom='DIP23-0010',
    statement='Гемопоэтические стволовые клетки направляют misfolded белки в агресомы Bag3-зависимо и зависят от аггрефагии; при выключении аутофагии они компенсируют это повышением активности протеасомы, но протеостаз всё равно нарушается, так как агрегаты накапливаются.',
    kind='condition',
    mechanism='маршрут очистки зафиксирован типом клетки; компенсаторный рост каталитической ёмкости протеасомы не спасает, потому что не восстанавливается доступность субстрата',
    conditions=['мышь, HSC in vivo', 'Bag3-дефицит', 'выключение аутофагии',
                'старение HSC (потеря агресом, снижение аутофагического потока)'],
    works=[{'doi': '10.1016/j.stem.2023.02.010', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'When autophagy is disabled, HSCs compensate by increasing proteasome activity, but proteostasis is ultimately disrupted as protein aggregates accumulate'}],
    tags=['capacity-compensation', 'aggrephagy', 'HSC', 'Bag3', 'availability'],
    notes='Прямой пример «насыщение деградации»: ёмкость протеасомы поднимается, но лимит уже не в ёмкости. Отличается от систем, где протеасома — главный путь: маршрут зависит от типа клетки.')

add(atom='DIP23-0011',
    statement='Одиночный агрегатный депозит, асимметрично наследуемый при репликативном старении дрожжей, сам по себе не сопровождается падением протеостаза: клетки с депозитом показывают усиленную деградацию цитозольных субстратов протеасомы и ненарушенный клиренс стресс-индуцированных агрегатов.',
    kind='measurement',
    mechanism='наличие агрегата не эквивалентно снижению доступности: депозит собирает неслучайный набор клиентов Hsp104/Hsp70-системы, а остальной цитозоль сохраняет деградационную способность',
    conditions=['Saccharomyces cerevisiae', 'Hsp42-зависимый депозит', 'репликативное старение',
                'сравнение клеток с депозитом и без'],
    works=[{'doi': '10.7554/elife.06197', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'the deposit-containing cells displayed enhanced degradation of cytosolic proteasome substrates and unimpaired clearance of stress-induced protein aggregates'}],
    tags=['ceiling', 'counterexample', 'deposit', 'proteostasis', 'yeast', 'Hsp42'],
    notes='Контрпример к простому правилу «агрегаты всегда снижают очистку». Потеря Hsp42 даёт симметричное наследование составляющих депозита и удлиняет жизнь материнской клетки. Знак эффекта противоположен DIP23-0001/0002, поэтому переносить его на клетки с большим грузом агрегатов нельзя: другая система (одиночный депозит, раннее старение).')

add(atom='DIP23-0012',
    statement='В просмотренной выборке не найдено работы, которая измеряла бы долю агрегированного белка, фактически доступную протеасоме или аутофагии, и связывала бы эту долю с моментом, когда ёмкость деградации перестаёт быть лимитирующей.',
    kind='gap',
    mechanism='обзор пространственного контроля качества описывает сайты секвестрации и их генетические детерминанты, но не даёт измеренной доли доступного пула',
    searched={'channels': ['OpenAlex works search', 'OpenAlex works/https://doi.org/<DOI> (проверка локаторов)'],
              'queries': ['proteasome accessibility protein aggregates degradation capacity',
                          'aggregate clearance rate autophagy half-life protein inclusions',
                          'proteasome overload saturation degradation capacity limitation',
                          'chaperone binding affinity damaged protein partitioning degradation',
                          'aggresome sequestration protects aggregates from proteasomal degradation',
                          'deposition site JUNQ IPOD partition misfolded protein degradation',
                          'fraction of aggregated protein degraded by proteasome versus autophagy quantified percent',
                          'proteasome degrades fraction of aggregated protein percent inaccessible steric'],
              'dates': '2026-11-23'},
    scope='Просмотрены аннотации ~90 работ по восьми запросам (выдача OpenAlex, per_page=15); полные тексты не читались. В выборке есть работы о маршрутах (UPS/аутофагия), о составе агресом, о конкуренции с шаперонами и одна работа с измеренными константами (DIP23-0008), но нет работы, где доля доступного агрегата выражена числом и одновременно показан переход ёмкости в лимитирующий режим.',
    conditions=['просмотренная выборка аннотаций, не полные тексты',
                'организмы: дрожжи, культивируемые клетки, мышь (HSC), in vitro Aβ'],
    works=[{'doi': '10.15252/embr.201643458', 'locator': 'abstract', 'access': 'abstract',
            'quote': 'we summarize findings on the nature of the different quality control sites identified in yeast'}],
    tags=['gap', 'accessible-fraction', 'saturation-threshold', 'spatial-quality-control'],
    notes='Формулировка ограничена выборкой («не найдено в просмотренной выборке»), а не утверждением об отсутствии в литературе. Вероятные места, где число может быть: полные тексты 10.1016/j.jbc.2022.102680, 10.1091/mbc.e14-08-1262, 10.1093/hmg/ddn157, 10.1074/jbc.m117.811448.')

out = pathlib.Path('literature/dips/reports')
(out / 'dip-2026-11-23-23.jsonl').write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in C) + '\n', encoding='utf-8')
print('cells', len(C))
ids = [x['atom'] for x in C]
assert len(set(ids)) == len(ids)
dois = [w['doi'] for x in C for w in x['works']]
print('works', len(dois), 'unique', len(set(dois)))
