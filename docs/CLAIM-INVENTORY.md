# CLAIM-INVENTORY — что граф утверждает на самом деле

Сгенерировано `python3 tools/claim_inventory.py --write`. **Не редактировать руками.**

Три элемента — это формулировка *замысла*, а не описание реализованного. Здесь показано, что из них
есть в графе, в каком виде и с каким происхождением.

Правило вердикта: элемент считается `implemented` только если найдён узел `kind: experiment` с
`provenance: verified_agent` или `human_confirmed`, в тексте которого элемент назван. Иначе — `claim`, `literature` или `absent`.

## E1. Граница как состояние, за которое платят

**Вердикт:** `claim`

узлов: 13; по видам: claim=10, definition=2, formula=1
по происхождению: extracted=11, verified_agent=2

| id | вид | происхождение | текст |
|---|---|---|---|
| `C-006` | claim | extracted | Полоса допуска — проекция ядра выживания на ось доли дохода, а её ширина — расстояние между границами выживани |
| `F-024` | formula | extracted | Ядро выживания и его граница |
| `L-018` | claim | extracted | Кожа как Markov blanket — и критика этой аналогии — Граница системы задаётся статистической независимостью вну |
| `L-037` | claim | extracted | **Пустое пересечение**: у моделей повреждения нет цены границы — «Модели старения (Chao, Borgqvist) **не имеют |
| `L-048` | claim | extracted | Порог ошибок Эйгена как безразмерная группа — `σ·q^ν > 1`; граница `μ_c = ln σ / ν`. |
| `L-066` | claim | extracted | Пространство выживания: граница как **геометрическая** величина — В **viability space** набор ограничений созд |
| `L-067` | claim | extracted | ITI: индивидуальность как **сохраняемая временная целостность** — «There is little agreement about what indivi |
| `L-087` | claim | extracted | Теория выживания на границе жизнь–смерть: заявка на недостающее — «Many cell models deal with constraints for  |
| `L-090` | claim | extracted | The “protocell”: A mathematical model of self-maintenance — самоподдержание протоклетки как динамика с подвижн |
| `L-093` | claim | extracted | Autopoiesis: The organization of living systems, its characterization and a model — Varela et al. 1974 — орган |
| `L-103` | claim | extracted | Self-maintenance and Self-reproduction in an Abstract Cell Model — Ono & Ikegami 2000 — самоподдержание и гран |
| `DEF-01` | definition | verified_agent | Граница — Поверхность, которую надо поддерживать, ценой вещества. |
| … | | | ещё 1 |

## E2. Повреждение бьёт по способности ремонтировать

**Вердикт:** `claim`

узлов: 1; по видам: claim=1
по происхождению: extracted=1

| id | вид | происхождение | текст |
|---|---|---|---|
| `L-107` | claim | extracted | Lipofuscin inhibits the proteasome by binding to surface motifs — Höhn et al. 2011 — титрование протеасомы лип |

## E3. Повреждение наследуется через воспроизводство

**Вердикт:** `claim`

узлов: 4; по видам: claim=4
по происхождению: extracted=4

| id | вид | происхождение | текст |
|---|---|---|---|
| `L-054` | claim | extracted | Наследование повреждения: модель «происхождения старения» — «At the start of a generation, each individual con |
| `L-076` | claim | extracted | Эффект матрицы: размер потомков **наследуется** без генов — «the size distribution of the newly formed vesicle |
| `L-096` | claim | extracted | Asymmetric segregation of protein aggregates is associated with cellular aging and rejuvenation — Lindner et a |
| `L-101` | claim | extracted | Statistical theory of asymmetric damage segregation in clonal cell populations — Найдено при починке чужого DO |

## Чем это отличается от намерения

Формулировка «в модели есть цена границы, повреждение бьёт по ремонтоспособности и это наследуется»
описывает **замысел**. В графе на сегодня: цена границы существует как статическое утверждение,
ремонтоспособность как переменная не названа ни разу, наследование присутствует только в
литературных узлах и гипотезах. Поэтому любые внешние тексты, написанные так, будто модель уже это
делает, описывают не модель, а план.
