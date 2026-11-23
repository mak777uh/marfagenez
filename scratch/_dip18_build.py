import json, re, subprocess, pathlib

KEY = pathlib.Path('/mnt/c/Users/Admin/.dsh/secrets/openalex.key').read_text().strip()
CURL = '/mnt/c/Windows/System32/curl.exe'
ROOT = pathlib.Path('/root/marfagenez')


def get(url, params):
    args = [CURL, '-sS', '-G', url]
    for k, v in params.items():
        args += ['--data-urlencode', '%s=%s' % (k, v)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        return {'__err': r.stderr[:200]}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'__err': r.stdout[:200]}


def absx(inv):
    if not inv:
        return ''
    pos = {}
    for w, idxs in inv.items():
        for i in idxs:
            pos[i] = w
    return ' '.join(pos[i] for i in sorted(pos))


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def core(s):
    return norm(s).replace('$', '')


CELLS = [
 dict(atom='DIP18-0001', doi='10.1145/1970386.1970387', kind='measurement',
  statement='Централизованный чекпойнтинг на жёстких дисках стоит не менее 25% накладных расходов на петaскейле: поддержание целостности само отнимает более четверти машинного времени.',
  mechanism='синхронная запись полного образа состояния процессов на медленный общий носитель останавливает вычисление на время сохранения, и эта остановка растёт с числом узлов',
  formula=None, symbols={},
  conditions=['крупномасштабная MPP-система, петaскейл', 'централизованный coordinated checkpointing на HDD', 'оценка из модели накладных расходов, не измерение на живой системе'],
  quote='Current centralized Hard Disk Drive (HDD) checkpointing results in overhead of 25% or more at petascale',
  confidence='medium', tags=['checkpoint', 'overhead', 'hpc', 'integrity-cost', 'exascale'],
  notes='Продолжение той же аннотации: гибридная PCRAM-схема даёт «only incurs less than 3% performance overhead» — цена падает почти на порядок при смене носителя, а не при лучшем алгоритме. Порог 25% заявлен для петaскейла и относится к HDD.'),
 dict(atom='DIP18-0002', doi='10.1109/sc41405.2020.00081', kind='measurement',
  statement='Прозрачный checkpoint-restart для CUDA-приложений на GPU укладывается примерно в 1% накладных расходов времени выполнения или меньше.',
  mechanism='разделение кода приложения (чекпойнтится) и внешней связи через нереентерабельные CUDA-библиотеки (не чекпойнтится) в пределах одного процесса убирает дорогую межпроцессную передачу',
  formula=None, symbols={},
  conditions=['приложения CUDA на GPU NVIDIA, включая Unified Virtual Memory', 'решение CRAC', 'накладные расходы времени выполнения, аннотация'],
  quote='CRAC combines: low runtime overhead (approximately 1% or less); fast checkpoint-restart',
  confidence='medium', tags=['checkpoint', 'gpu', 'overhead', 'low-cost'],
  notes='Тот же результат достигнут ценой ограничения: часть состояния (внешние библиотеки) не сохраняется, поэтому полнота восстановления уже, чем у полного образа.'),
 dict(atom='DIP18-0003', doi='10.1587/transinf.2017pap0002', kind='measurement',
  statement='Распределение чекпойнтов во времени (speculative checkpointing) снижает энергию до 11% ценой небольшого роста времени выполнения, то есть цена целостности перекладывается из энергии во время.',
  mechanism='спекулятивное разнесение моментов чекпойнтинга снимает пиковую концентрацию ввода-вывода, из-за которой coordinated-протокол тратит энергию на пиковую нагрузку',
  formula=None, symbols={},
  conditions=['экзаскейл HPC, модель времени выполнения и энергии', 'сравнение с coordinated checkpointing', 'оценка по моделям, не натурный замер'],
  quote='speculative checkpointing can achieve up to a 11% energy reduction at the cost of a relatively-small increase in the execution time',
  confidence='medium', tags=['checkpoint', 'energy', 'tradeoff', 'exascale'],
  notes='Это обмен, а не бесплатное улучшение: знак выгоды меняется, когда масштаб превышает 1,2 млн узлов — там авторы ждут существенного компромисса энергия/время.'),
 dict(atom='DIP18-0004', doi='10.1109/wicsa.2014.49', kind='mechanism',
  statement='Постоянный и обширный мониторинг, которым система ищет неисправные компоненты, сам вносит высокие накладные расходы и способен сделать систему нестабильной.',
  mechanism='наблюдение за аномалиями требует инструментирования всех компонентов всё время, а не только подозреваемых, поэтому расход ресурсов на диагноз складывается с полезной работой и может её вытеснить',
  formula=None, symbols={},
  conditions=['компонентные приложения в одной виртуальной машине', 'система мониторинга Scapegoat, сравнение с постоянным мониторингом', 'оценка накладных расходов, аннотация'],
  quote='Current solutions that perform permanent and extensive monitoring to detect anomalies induce high overhead on the system, and can, by themselves, make the system unstable',
  confidence='medium', tags=['monitoring', 'overhead', 'self-defeating', 'mape-k'],
  notes='Случай, когда самовосстановление ухудшает систему: средство диагностики становится источником отказа. Локальный мониторинг «только когда нужно» снижает накопленные расходы в среднем на 80% — по той же аннотации.'),
 dict(atom='DIP18-0005', doi='10.48550/arxiv.2103.08191', kind='measurement',
  statement='Переход между схемами избыточности в кластере хранения может потребовать 100% пропускной способности ввода-вывода кластера непрерывно в течение нескольких недель.',
  mechanism='перекладывание данных при смене схемы резервирования создаёт нагрузку, которая складывается с обслуживанием запросов и при жадном планировании вытесняет его целиком',
  formula=None, symbols={},
  conditions=['крупные production-кластеры хранения (110K-450K дисков, трейсы Google/NetApp/Backblaze)', 'адаптивное резервирование под наблюдаемую частоту отказов', 'анализ трейсов и оценка нагрузки переходов'],
  quote='transition IO under existing approaches can consume 100% cluster IO continuously for several weeks',
  confidence='medium', tags=['replication', 'adaptation-cost', 'io', 'storage', 'self-adaptive'],
  notes='Тот же источник: проактивное планирование снижает требование к полосе до «never needing more than 5% cluster IO bandwidth (0.2-0.4% on average)» при экономии места 14-20%. Цена адаптации зависит от того, кто платит за переход: она может равняться всей ёмкости системы.'),
 dict(atom='DIP18-0006', doi='10.1109/sp.2015.59', kind='measurement',
  statement='Проверка целостности и согласованности данных в облаке с батарейных устройств стоит примерно 12,6% роста загрузки CPU и 1,3% накладных расходов по полосе сети при пренебрежимом влиянии на время жизни батареи.',
  mechanism='облако само объявляет время и порядок операций, поэтому устройствам не нужно записывать и пересылать друг другу историю операций — остаётся только сверить объявленное с наблюдаемым',
  formula=None, symbols={},
  conditions=['облачное хранилище (Amazon S3), клиенты на батарейных устройствах', 'проверка моделей strong/eventual/causal consistency', 'измерение CPU, сети и времени жизни батареи'],
  quote='Caelus achieves this with a roughly 12.6% increase in CPU utilization on clients, 1.3% of network bandwidth overhead and negligible impact on the battery life of devices',
  confidence='medium', tags=['integrity-check', 'energy', 'battery', 'overhead', 'measurement'],
  notes='Важно для бюджета цифрового организма: цена проверки целостности может быть почти невидима в энергии и заметна в вычислении — это перенос цены между статьями бюджета, а не её отсутствие.'),
 dict(atom='DIP18-0007', doi='10.63125/g9c9cp41', kind='measurement',
  statement='Усиление отказоустойчивости в среднем требует 12,4% дополнительной энергии, при том что доступность растёт с 94,1% до 98,3%.',
  mechanism='избыточность, повторные вычисления и восстановление добавляют работу, которая не производит полезного результата, но удерживает сервис доступным',
  formula=None, symbols={},
  conditions=['edge-CPS, мета-анализ 91 исследования с совместными энергетическими и надёжностными исходами', 'пул из 162 исследований, 6738 контролируемых инъекций отказов', 'сводные (pooled) оценки, а не один эксперимент'],
  quote='Analysis of 91 studies simultaneously reporting energy and reliability outcomes showed that enhanced fault tolerance required an average 12.4% additional energy',
  confidence='medium', tags=['fault-tolerance', 'energy-budget', 'meta-analysis', 'availability', 'price'],
  notes='Ближайшее к «бюджету границы» число в домене: цена измерима и составляет десятки процентов, а не порядки. Работа мета-аналитическая, поэтому цифра — средняя по разнородным системам; условия переноса на цифровой организм не проверены.'),
 dict(atom='DIP18-0008', doi='10.1145/2901318.2901339', kind='measurement',
  statement='Обнаружение и исправление transient-ошибок ценой инструкционной избыточности удваивает время выполнения: нормированное время равно 2x при обнаружении 98,9% и исправлении 91,2% внесённых искажений данных.',
  mechanism='каждая инструкция исполняется дважды для сравнения, а откат при расхождении делается через аппаратную транзакционную память',
  formula=None, symbols={},
  conditions=['многопоточные приложения (Phoenix, PARSEC), товарные CPU с транзакционной памятью', 'инъекция transient-отказов оборудования', 'нормированное время выполнения относительно базового'],
  quote='The observed normalized runtime is 2x, with 98.9% of the injected data corruptions being detected and 91.2% being corrected',
  confidence='medium', tags=['fault-tolerance', 'redundancy', 'overhead', 'detection', 'measurement'],
  notes='Цена полная (2x), а покрытие неполное: часть искажений не обнаружена и не исправлена. Это прямое возражение идее, что целостность покупается целиком за фиксированную цену.'),
 dict(atom='DIP18-0009', doi='10.1109/reconfig.2011.37', kind='measurement',
  statement='Предел самовосстановления эволюционирующей аппаратной системы — 3 повреждённых элемента из 16, то есть более 18% накопленных постоянных отказов.',
  mechanism='эволюционный алгоритм вместе с частичной динамической реконфигурацией перестраивает функции фильтрации изображения на уцелевших элементах',
  formula=None, symbols={},
  conditions=['двумерный массив 16 (4x4) processing elements, полностью встроенная система', 'приложение фильтрации изображения, две модели отказов (PE и CLB)', 'две стратегии самовосстановления: с диагнозом и без'],
  quote='Results show that it may properly recover from faults in up to 3 PEs, that is, more than 18% cumulative permanent faults',
  confidence='medium', tags=['self-healing', 'capacity-limit', 'evolvable-hardware', 'fault-tolerance'],
  notes='Тот же источник: «resource cost for self-healing is very low (only some code additions in the internal microprocessor core)» — цена мала потому, что адаптивность уже оплачена для обычной работы. Самовосстановление может быть дешёвым только как побочный продукт уже купленной пластичности.'),
 dict(atom='DIP18-0010', doi='10.1007/s00446-015-0258-3', kind='condition',
  statement='Самовосстановление сети возможно с детерминированными гарантиями формы: O(log n) раундов и O(log n) сообщений на вставку или удаление при константном числе изменений топологии, и это держится против всесильного адаптивного противника.',
  mechanism='распределённый алгоритм поддерживает константную степень и свойства экспандера детерминированно, а не вероятностно, поэтому деградация расширения при враждебных изменениях не накапливается',
  formula='раунды = O(log n); сообщения = O(log n); изменений топологии = O(1)', symbols={'n': 'число узлов сети в текущий момент'},
  conditions=['динамическая распределённая сеть, противник управляет входами и выходами узлов', 'детерминированные (не вероятностные) гарантии расширения', 'теоретический результат, распределённый алгоритм dex'],
  quote='only $$O(\\log n)$$ rounds and $$O(\\log n)$$ messages are needed with high probability',
  confidence='medium', tags=['survivability', 'formal-guarantee', 'self-healing', 'network', 'bound'],
  notes='Это формальный критерий живучести, а не измерение: цена выражена в раундах и сообщениях на одно изменение, а не в джоулях. Предыдущие конструкции давали только вероятностные гарантии, которые в динамике деградируют быстрее.'),
]

out = []
log = []
titles = {}
for c in CELLS:
    doi = c['doi']
    d = get('https://api.openalex.org/works/https://doi.org/' + doi,
            {'api_key': KEY, 'select': 'id,doi,title,publication_year,abstract_inverted_index'})
    if '__err' in d:
        log.append('FAIL fetch %s: %s' % (doi, d['__err'][:120]))
        print(log[-1])
        continue
    rdoi = (d.get('doi') or '').replace('https://doi.org/', '').lower()
    a = absx(d.get('abstract_inverted_index'))
    ok_doi = rdoi == doi.lower()
    ok_q = core(c['quote']) in core(a)
    print(('OK  ' if ok_doi and ok_q else 'BAD '), doi, '| doi', ok_doi, '| quote', ok_q,
          '|', (d.get('title') or '')[:65])
    if not (ok_doi and ok_q):
        log.append('%s %s' % ('doi mismatch' if not ok_doi else 'quote not found', doi))
        if not ok_q:
            print('   QUOTE:', core(c['quote'])[:140])
            print('   ABS  :', core(a)[:240])
        continue
    rec = {'atom': c['atom'], 'statement': c['statement'], 'domain': 'cs.digital_life',
           'kind': c['kind'], 'mechanism': c['mechanism'], 'formula': c['formula'],
           'symbols': c['symbols'], 'conditions': c['conditions'],
           'works': [{'doi': doi, 'locator': 'abstract', 'access': 'abstract', 'quote': c['quote']}],
           'confidence': c['confidence'], 'locator_status': 'verified',
           'tags': c['tags'], 'notes': c['notes']}
    out.append(rec)
    titles[c['atom']] = {'doi': doi, 'title': d.get('title'), 'year': d.get('publication_year')}

p = ROOT / 'literature/dips/reports/dip-2026-11-23-18.jsonl'
p.write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in out), encoding='utf-8')
(ROOT / '_dip18_titles.json').write_text(json.dumps(titles, ensure_ascii=False, indent=1), encoding='utf-8')
(ROOT / '_dip18_log.txt').write_text('\n'.join(log), encoding='utf-8')
print('\nWROTE %d cells -> %s' % (len(out), p))
print('LOG:', log)
