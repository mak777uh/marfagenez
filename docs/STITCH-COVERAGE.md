# Покрытие карты знаний литературной опорой

Сгенерировано `tools/stitch_coverage.py`. Пара = у узла `kg/` есть `data.lit_ref` (ячейки литературной карты, сшитые с ним вручную).

Прогоны (`experiment`), объекты свидетельства (`evidence`) и определения в счёт не идут: это не утверждения о мире.

## Сводка

Утверждений, формул, дыр и соответствий: **152**; с литературной опорой: **16** (11%).

| вид | всего | с опорой |
|---|---|---|
| claim | 116 | 6 |
| formula | 31 | 9 |
| gap | 3 | 1 |
| correspondence | 2 | 0 |

## Узлы с опорой

| узел | вид | опора |
|---|---|---|
| C-001 | claim | B26-01-0001, DIP56-0004, DIP56-0007 |
| C-002 | claim | B26-01-0001, B26-01-0009, DIP56-0003, DIP57-0002, DIP57-0006, DIP57-0008, DIP57-0009, DIP57-0010 |
| C-003 | claim | B26-01-0004 |
| C-005 | claim | B22-01-0001, B26-01-0003, B26-01-0007 |
| C-006 | claim | B22-01-0006 |
| C-008 | claim | DIP58-0001, DIP58-0008, DIP58-0010 |
| F-001 | formula | B21-01-0001, DIP48-0010, DIP49-0005 |
| F-002 | formula | DIP48-0008, DIP52-0003, DIP52-0005, DIP57-0002 |
| F-003 | formula | B22-01-0001, B23-01-0002, DIP47-0004, DIP49-0003, DIP51-0001, DIP51-0006, DIP56-0002, DIP57-0005 |
| F-005 | formula | DIP56-0005 |
| F-006 | formula | B24-01-0003, DIP51-0004 |
| F-014 | formula | B20-01-0002, B20-02-0001, B25-01-0001, DIP46-0009, DIP52-0001, DIP52-0011, DIP52-0012, DIP53-0002, DIP57-0006 |
| F-021 | formula | DIP49-0010, DIP51-0008, DIP53-0002, DIP53-0006, DIP53-0009, DIP56-0004, DIP56-0005, DIP56-0007, DIP56-0009 |
| F-024 | formula | B18-01-0003, B21-01-0004, B26-01-0008, DIP49-0001, DIP49-0002, DIP49-0006, DIP53-0003, DIP53-0005 |
| F-029 | formula | B22-01-0004, DIP46-0001, DIP47-0002, DIP47-0003, DIP53-0011 |
| GAP-02 | gap | B24-01-0003 |

## Узлы без опоры (самое важное)

| узел | вид | статус | текст |
|---|---|---|---|
| C-004 | claim | established | Порог равновесия при симметричном делении у Chao: Πλ ≤ 1/6. |
| C-007 | claim | refuted | Показатель расходимости равен 1/(m+1), где m — число каналов удаления. |
| CORR-01 | correspondence | hypothesis | Соответствие ОПРОВЕРГНУТО в прежней формулировке: «полоса допуска = проекция ядра выживани |
| CORR-02 | correspondence | hypothesis | Соответствие: наша теневая цена — производная функции значения по ресурсу; у Warren & Jone |
| F-004 | formula | hypothesis | Цена поддержания и замыкание |
| F-007 | formula | hypothesis | Порог ошибок |
| F-008 | formula | hypothesis | Viability kernel |
| F-009 | formula | hypothesis | Замыкание ограничений (структурное) |
| F-010 | formula | hypothesis | RAF |
| F-011 | formula | hypothesis | Ниша и её изменение |
| F-012 | formula | hypothesis | Многоуровневый отбор (Прайс) |
| F-013 | formula | hypothesis | Цепь рождения–смерти и «честная вероятность» как медиана |
| F-015 | formula | hypothesis | Sizer / adder / timer |
| F-016 | formula | hypothesis | Цена страховки (Тулджапурак) |
| F-017 | formula | hypothesis | Порог ошибок Эйгена |
| F-018 | formula | hypothesis | Показатель и порядок нелинейности |
| F-019 | formula | hypothesis | Критерий равновесия Chao (подтверждён локатором) |
| F-020 | formula | hypothesis | Надёжность: Гомпертц, Макегам и плато из избыточности |
| F-022 | formula | established | Замыкание как свойство графа |
| F-023 | formula | established | Двойственная задача и смысл цены |
| F-025 | formula | hypothesis | ITI: разложение временной информации |
| F-026 | formula | hypothesis | Зерно среды задаёт тип bet-hedging |
| F-027 | formula | hypothesis | Цена роста против цены удержания |
| F-028 | formula | hypothesis | Adder, sizer и линии родства |
| F-030 | formula | hypothesis | Метрики открытости (если понадобятся) |
| F-031 | formula | hypothesis | Внутреннее ограничение выживания из графа |
| GAP-01 | gap | hypothesis | Разрыв: наша доля в наибольшей SCC и замыкание ограничений литературы — не одно и то же. |
| GAP-03 | gap | hypothesis | Разрыв: цена удержания как механизм устойчивости — статическая LP и динамическое ядро не с |
| L-001 | claim | hypothesis | Накопление повреждения даёт экспоненциальный рост смертности — В простой модели накопления |
| L-002 | claim | hypothesis | Мёртвое плато — то, что модели накопления воспроизводят плохо — Стандартные модели накопле |
| L-003 | claim | hypothesis | Disposable soma: ресурс делится между починкой и потомством, оптимум явно моделируется — « |
| L-004 | claim | hypothesis | Оптимальная доля и закон Гомпертца выводятся вместе — Динамическое программирование даёт * |
| L-005 | claim | hypothesis | Порог доли удержания повреждения известен — «a cell lineage dividing symmetrically is **im |
| L-006 | claim | hypothesis | Все кривые выживания — растяжения одной — Кривые выживания при разных вмешательствах совпа |
| L-007 | claim | hypothesis | Страховка сдвигает оптимум с пика на пологий склон — «insurance causes the optimal phenoty |
| L-008 | claim | hypothesis | Bet-hedging и банк семян — При **мультипликативном** критерии приспособленности и стохасти |
| L-009 | claim | hypothesis | Насыщаемое удаление и порог: прямой аналог — Удаление повреждения насыщается, и из этого с |
| L-010 | claim | hypothesis | Теория надёжности: отказ как выброс нагрузки — Организм — система с отказами; смертность р |
| L-011 | claim | hypothesis | Frailty и vitality: две системы с равным состоянием не равны — Скрытая переменная (хрупкос |
| L-012 | claim | hypothesis | DEB: правило κ и приоритет поддержания — Энергия делится: доля κ идёт на соматическое подд |
| L-013 | claim | hypothesis | Pirt и поддержание у микробов — Часть энергии уходит на поддержание, не на рост; есть «коэ |
| L-014 | claim | hypothesis | Две независимые опасности и оптимальный ремонт — «evolution could select for its complete  |
| L-015 | claim | hypothesis | Замкнутость ограничений — возможно, **их** определение нашего критерия — Живое — система,  |
| L-016 | claim | hypothesis | Химотон: три подсистемы и требование замкнутости — Минимальная живая единица — **три** под |
| L-017 | claim | hypothesis | Индивидуальность как передача информации — Индивидуальность — это **мера** (передача инфор |
| L-018 | claim | hypothesis | Кожа как Markov blanket — и критика этой аналогии — Граница системы задаётся статистическо |
| L-019 | claim | hypothesis | Автономия как базовая организация — Базовая автономия — способность системы поддерживать с |
| L-020 | claim | hypothesis | Катастрофа ошибок и порог точности — Есть **порог точности копирования**, ниже которого на |
| L-021 | claim | hypothesis | Минимальная клетка: ограничение кинетическое, а не энергетическое — Самоподдерживающаяся м |
| L-022 | claim | hypothesis | Несовместимость с disposable soma — сигнал, а не баг — Если при `c ≤ 1` кожа поддерживаетс |
| L-023 | claim | hypothesis | Модель Chao, восстановленная по тексту: порог `Πλ = 1/6`, и это **складка** — У Чао асимме |
| L-024 | claim | hypothesis | Смертность как канал удаления превращает складку в непрерывную расходимость — «смертность  |
| L-025 | claim | hypothesis | Замыкание ограничений: структура, а не баланс — Замыкание — **причинная сеть взаимно подде |
| L-026 | claim | hypothesis | Химические организации: формальное замыкание множеств — Формальное определение **самоподде |
| L-027 | claim | hypothesis | RAF-множества: замыкание есть, универсальной доли нет — RAF определимо формально (каждая р |
| L-028 | claim | hypothesis | Viability: выживание — множество траекторий, а не мгновенный порог — Viability kernel — ** |
| L-029 | claim | hypothesis | Порог ошибок Эйгена: точность против длины — Максимальная длина, удерживаемая отбором, огр |
| L-030 | claim | hypothesis | Термодинамика замыкания: цены есть, универсальной формулы нет — Работа на поддержание огра |
| L-031 | claim | hypothesis | Индивидуальность: единого теста нет — Списки критериев есть, единого операционального тест |
| L-032 | claim | hypothesis | Assembly theory: сложность сборки, но не организация — Индекс сборки измеряет **сложность* |
| L-033 | claim | hypothesis | Протоклетки: числа по проницаемости и делению — Есть измеренные проницаемости и условия ро |
| L-034 | claim | hypothesis | Niche construction: обратная связь есть, скалярной меры нет — Записывают **ΔR** (разницу с |
| L-035 | claim | hypothesis | Cliff-edge, риск и оптимальность — У обрыва оптимум сдвигается; риск-чувствительные страте |
| L-036 | claim | hypothesis | Надёжность: `μ` как интенсивность отказов — Смертность — интенсивность отказов системы с з |
| L-037 | claim | hypothesis | **Пустое пересечение**: у моделей повреждения нет цены границы — «Модели старения (Chao, B |
| L-038 | claim | hypothesis | Bet-hedging: критерий и три ловушки — Bet-hedging — жертва средним ради снижения дисперсии |
| L-039 | claim | hypothesis | Скалярная память: максимум смещён (winner's curse), стандарт — UCB — `E[max]` из `n` шумны |
| L-040 | claim | hypothesis | Калибровка и sharpness — стандартные метрики — Brier (бинарное), CRPS (непрерывное); калиб |
| L-041 | claim | hypothesis | Sizer / adder / timer: канон регуляции размера — Три механизма; параметризация `s_d = a·s_ |
| L-042 | claim | hypothesis | Chemical organization theory: формальное замыкание — Организация — множество видов, **замк |
| L-043 | claim | hypothesis | RAF: три разные задачи, и только две полиномиальны — Максимальная RAF — **полиномиально**; |
| L-044 | claim | hypothesis | Экологическая стехиометрия: возврат вещества в среду — Потребители возвращают азот и фосфо |
| L-045 | claim | hypothesis | Надёжность и Гомпертц без постулата `μ` — Избыточность с начальным грузом дефектов и её ис |
| L-046 | claim | hypothesis | Error catastrophe: известный отрицательный результат — Наивная самоссылка (ошибки поврежда |
| L-047 | claim | hypothesis | Интегральная обратная связь: среднее держится, дисперсия растёт — Интегральная связь даёт  |
| L-048 | claim | hypothesis | Порог ошибок Эйгена как безразмерная группа — `σ·q^ν > 1`; граница `μ_c = ln σ / ν`. |
| L-049 | claim | hypothesis | Один прибор: калибровка исследователя = калибровка организма — Лог-счёт по strictly proper |
| L-050 | claim | hypothesis | COT + потоки = LP, и «цена» как двойственная переменная — К организации добавляются ограни |
| L-051 | claim | hypothesis | Порог `Πλ = 1/6` **подтверждён локатором** — Порог симметричного деления — `Πλ ≤ 1/6`; при |
| L-052 | claim | hypothesis | Асимметричное деление **протоклеток** — ближайший сосед нашего пересечения — Устойчивый ро |
| L-053 | claim | hypothesis | Стохастическая модель старения: повреждение, починка, асимметрия деления — Детерминированн |
| L-054 | claim | hypothesis | Наследование повреждения: модель «происхождения старения» — «At the start of a generation, |
| L-055 | claim | hypothesis | Надёжность: Гомпертц **и плато** из исчерпания избыточности — «According to the Gompertz l |
| L-056 | claim | hypothesis | Плато смертности как установленный феномен, а не артефакт — Позднее плато смертности — **н |
| L-057 | claim | hypothesis | Одноклеточные делят ресурс между **асимметричным распределением** и **починкой** — В модел |
| L-058 | claim | hypothesis | Кривые выживания выводятся из **оптимального распределения ресурса** — Интенсивность почин |
| L-059 | claim | hypothesis | DEB: правило κ, приоритет поддержания и голодание — Энергия делится **правилом κ**: доля κ |
| L-060 | claim | hypothesis | Графы «процесс–обеспечение»: замыкание становится вычислимым — Разные теории самоорганизац |
| L-061 | claim | hypothesis | Формальное условие замыкания ограничений (цитата) — «We characterize biological organizati |
| L-062 | claim | hypothesis | Двойственные переменные LP — это **химические потенциалы** — «the dual to the linear progr |
| L-063 | claim | hypothesis | COT как **структурная** рамка, независимая от кинетики — COT даёт **структурную и алгебраи |
| L-064 | claim | hypothesis | Инвариант из стехиометрии и цена предположения о стационарности — (1) Консервативные поток |
| L-065 | claim | hypothesis | Ядро выживания: определение и **алгоритм** — «The subset of evolutions viable in K is deno |
| L-066 | claim | hypothesis | Пространство выживания: граница как **геометрическая** величина — В **viability space** на |
| L-067 | claim | hypothesis | ITI: индивидуальность как **сохраняемая временная целостность** — «There is little agreeme |
| L-068 | claim | hypothesis | Информационная индивидуальность **требует причинности**, а не корреляции — Информационные  |
| L-069 | claim | hypothesis | ΦID: разложение информационной динамики на шесть режимов — ΦID даёт **таксономию** информа |
| L-070 | claim | hypothesis | Приближение Тулджапурака: цена дисперсии — **число** — При **малой вариации** и **отсутств |
| L-071 | claim | hypothesis | Диверсификация стоит дорого, и её темп — не универсален — Bet-hedging через диверсификацию |
| L-072 | claim | hypothesis | Зерно среды и число решений решают, **какой** bet-hedging работает — **Мультипликативное** |
| L-073 | claim | hypothesis | Рост мембраны протоклетки: **скорость зависит от внешнего липида** — «The autocatalytic re |
| L-074 | claim | hypothesis | Проницаемость как **движущая сила отбора** — Устойчивость везикулы зависит от **состава ли |
| L-075 | claim | hypothesis | Критерий «когда реакционная сеть — метаболизм», поддерживающий рост и деление — Сформулиро |
| L-076 | claim | hypothesis | Эффект матрицы: размер потомков **наследуется** без генов — «the size distribution of the  |
| L-077 | claim | hypothesis | Прямая и обратная линия родства дают **разные средние** — «the mean cell size in a **forwa |
| L-078 | claim | hypothesis | Adder: клетка добавляет **постоянную** величину, а не тянется к размеру — В устойчивом рос |
| L-079 | claim | hypothesis | Предсказание adder в числах: `CV² = ln 4 − 1` — При `β = 1/2` с вероятностью один «`CV²_s  |
| L-080 | claim | hypothesis | Нормальные формы трёх локальных бифуркаций — «saddle-node: `ṅ = r + n²`; transcritical: `ṅ |
| L-081 | claim | hypothesis | Классы универсальности и показатели для трёх бифуркаций — Сходимость к неподвижной точке * |
| L-082 | claim | hypothesis | Несовершенная бифуркация: **шум сглаживает переход** — У реальных систем есть **несовершен |
| L-083 | claim | hypothesis | Симуляция против реализации: что мы вправе утверждать — Различаются **симуляция** (модель, |
| L-084 | claim | hypothesis | Как **мерить** открытость: набор метрик и его критика — Открытость меряют **Levenshtein**, |
| L-085 | claim | hypothesis | Оценка открытости **субъективна**, и это признано — Определение открытости «удивительно тр |
| L-086 | claim | hypothesis | Ограничение выживания **выводится** из графа процессов — и это уже сделано — Граф включает |
| L-087 | claim | hypothesis | Теория выживания на границе жизнь–смерть: заявка на недостающее — «Many cell models deal w |
| L-088 | claim | hypothesis | Viability ≠ survival: различение, которого нам не хватало — «**Survival** describes an **o |
| L-089 | claim | hypothesis | Minimal Conditions for Protocell Stationary Growth — минимальные условия стационарного рос |
| L-090 | claim | hypothesis | The “protocell”: A mathematical model of self-maintenance — самоподдержание протоклетки ка |
| L-091 | claim | hypothesis | Synergistic effects of repair, resilience and retention of damage determine the conditions |
| L-092 | claim | hypothesis | Balance between asymmetric allocation and repair of somatic damage in unicellular life for |
| L-093 | claim | hypothesis | Autopoiesis: The organization of living systems, its characterization and a model — Varela |
| L-094 | claim | hypothesis | Biological organisation as closure of constraints — Montévil & Mossio 2015 — организация к |
| L-095 | claim | hypothesis | Detecting autocatalytic, self-sustaining sets in chemical reaction systems — Hordijk & Ste |
| L-096 | claim | hypothesis | Asymmetric segregation of protein aggregates is associated with cellular aging and rejuven |
| L-097 | claim | hypothesis | THE MAINTENANCE OF THE ACCURACY OF PROTEIN SYNTHESIS AND ITS RELEVANCE TO AGEING — Orgel 1 |
| L-098 | claim | hypothesis | Stochastic modeling of aging cells reveals how damage accumulation, repair, and cell-divis |
| L-099 | claim | hypothesis | Evolution of ageing — Kirkwood 1977 — эволюция старения: компромисс ремонта и размножения |
| L-100 | claim | hypothesis | Selforganization of matter and the evolution of biological macromolecules — Eigen 1971 — с |
| L-101 | claim | hypothesis | Statistical theory of asymmetric damage segregation in clonal cell populations — Найдено п |
| L-102 | claim | hypothesis | A network theory of ageing: the interactions of defective mitochondria, aberrant proteins, |
| L-103 | claim | hypothesis | Self-maintenance and Self-reproduction in an Abstract Cell Model — Ono & Ikegami 2000 — са |
| L-104 | claim | hypothesis | Thirty Years of Computational Autopoiesis: A Review — McMullin & Varela 2004 — реимплемент |
| L-105 | claim | hypothesis | Closure to efficient causation, computability and artificial life — Cárdenas et al. 2010 — |
| L-106 | claim | hypothesis | Proteasome inhibition by lipofuscin/ceroid during postmitotic aging of fibroblasts — Sitte |
| L-107 | claim | hypothesis | Lipofuscin inhibits the proteasome by binding to surface motifs — Höhn et al. 2011 — титро |
| L-108 | claim | hypothesis | Damage dynamics and the role of chance in the timing of E. coli cell death — Damage dynami |

## Что это значит

1. **Опора есть у 16 из 152** — остальные наши утверждения пока живут без
   внешней пары. Это не значит, что они неверны: часть из них — наши собственные конструкции
   (пороги, ядра, цены), которым в литературе соответствует не одна работа, а класс явлений.
2. **Без опоры остались целые механизмы:** обмен, организация, смерть, агентность. Ровно те, у
   которых в `kg/` не было хабов до круга 519, — совпадение не случайное: нет литературы, нет и связи.
3. **Самое дешёвое следующее движение** — искать литературу не под формулы (они уже сшиты), а под
   утверждения `C-00*` без опоры: у них есть проверенные числа и понятный вопрос к литературе.

## Чего это не даёт

- Покрытие — не подтверждение: `kg_ref` говорит «связано», а не «верно».
- Число пар зависит от моей ручной разметки, а не от полноты поиска.
