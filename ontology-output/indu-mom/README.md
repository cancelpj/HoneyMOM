# HoneyMOM 制造运营本体

用 `wuming-ontology` 技能对 [Indu-mom](https://github.com/agentthink/Indu-mom)(HoneyMOM 制造运营系统)
梳理的业务本体产物。

## 交付物

| 文件 | 说明 |
| --- | --- |
| `honeymom.ttl` | OWL Turtle 本体,UTF-8 —— **唯一真源** |
| `honeymom.html` | 离线可视化页面,自包含 CSS/JS/数据,双击即可打开 |
| `honeymom.owx` | 同一模型的 **OWL/XML** 序列化(Protégé 原生格式) |
| `honeymom.ofn` | 同一模型的 **Functional Syntax** 序列化(Protégé 另一种原生格式) |
| `honeymom.omn` | 同一模型的 **Manchester Syntax** 序列化(OWL 编辑器通用语法) |
| `honeymom.rdf` | 同一模型的 **RDF/XML** 序列化(便于 Jena 等 RDF 工具链) |
| `honeymom.jsonld` | 同一模型的 JSON-LD 序列化(便于前端 / JSON-LD 工具链) |
| `honeymom.nt` | 同一模型的 N-Triples 序列化(便于逐行 diff / 流式处理) |
| `tools/extract_entities.py` | 从 `honeymom/schema*.py` 静态抽取实体模型的工具(证据溯源用) |
| `tools/verify_with_owlapi.js` | 用 Protégé 自带 OWL API 做公理层校验 + HermiT 推理 + 导出 OWL 序列化 |
| `tools/regenerate_all.py` | 一条命令重建全部产物并做一致性校验 |
| `tools/_bisect_turtle.py` | TTL 语法逐块定位工具(改本体后自查用) |

> 其余七个文件都是 **Turtle 的等价序列化**,不是独立模型。任何修改都只应改 `honeymom.ttl`,
> 然后跑 `python tools/regenerate_all.py` 重生成。

## 关于 OWL / 各种序列化

**`.ttl` 本身就是 OWL 2 本体** —— 文件里用的就是 `owl:Class`、`owl:ObjectProperty`、
`owl:DatatypeProperty`、`owl:disjointWith`、`owl:inverseOf`、`owl:hasKey`、
`rdf:type owl:FunctionalProperty` 这套 OWL 词汇。Turtle 只是 OWL/RDF 模型的**一种序列化**。
Protégé 直接打开 `.ttl` 即可,不需要转换。

各种序列化由 **Protégé 自带的官方 OWL API 渲染器**生成(Protégé 用的就是同一套 API,
所以格式天然兼容),校验也由官方解析器回读完成:

| 格式 | 文件 | 生成方式 | 官方解析器回读 |
| --- | --- | --- | --- |
| OWL/XML | `honeymom.owx` | OWL API `OWLXMLDocumentFormat` | ✅ 源公理 100% 保留 |
| Functional Syntax | `honeymom.ofn` | OWL API `FunctionalSyntaxDocumentFormat` | ✅ 源公理 100% 保留 |
| Manchester Syntax | `honeymom.omn` | OWL API `ManchesterSyntaxDocumentFormat` | ✅ 源公理 100% 保留 |
| RDF/XML | `honeymom.rdf` | OWL API `RDFXMLDocumentFormat` | ✅ 源公理 100% 保留 |
| JSON-LD | `honeymom.jsonld` | rdflib | ✅ 与源图同构 |
| N-Triples | `honeymom.nt` | rdflib | ✅ 与源图同构 |

两个必须知道的坑:

- **OWL/XML 不是 RDF/XML。** 元素名在 OWL/XML 里表示"类型"、在 RDF/XML 里表示"谓词"。
  而且 OWL API 4.5 的 OWL/XML 解析器底层是 RDF/XML 解析器,**要求 `rdf:RDF` 根元素**。
  手写 `.owx` 很容易不被接受(本项目最初手写过一版,官方解析器直接拒收),
  所以一律用官方渲染器导出,不要自己拼 XML。
- **互斥性在 RDF/XML 里用列表编码**(`owl:AllDisjointClasses` + `rdf:parseType="Collection"`),
  而不是逐对 `owl:disjointWith` 三元组。两种编码语义等价,但逐三元组比较必然不等,
  所以 `.rdf` 的判据在**公理层**(源公理一条都不能丢),不在三元组层。

## Protégé 安装(本机)

| 项 | 值 |
| --- | --- |
| 安装位置 | `C:\ProgramData\Protege-5.6.9`(所有用户可访问) |
| 版本 | Protégé 5.6.9 for Windows(zip 版,自带 JRE) |
| 内置 JRE | OpenJDK 11.0.25 Temurin(无需另装 Java) |
| 体积 | 396 文件 / 193.6 MB + `lib-extra` 37 个 jar(OWL API 运行时依赖) |
| 启动 | `C:\ProgramData\Protege-5.6.9\Protege.exe` |
| 快捷方式 | 当前用户的开始菜单 + 桌面已建;**全用户**开始菜单 / 公共桌面 / 系统 PATH 需管理员,见下 |

`lib-extra/` 里是给**无头校验**用的补充依赖,不影响 Protégé 正常运行:

- `caffeine-2.9.3.jar` —— OWL API 的缓存依赖
- `rdf4j-*3.7.7.jar` 等 30 个 —— 按 `owlapi-osgidistribution.jar` 的 MANIFEST 声明补齐的 RDF4J
- `automaton-1.11-8.jar` 等 6 个 —— 从 HermiT 插件 jar 里解出的内嵌依赖

需要管理员权限的三步(全用户开始菜单 + 公共桌面 + 系统 PATH),用管理员 PowerShell 执行:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\ProgramData\Protege-5.6.9\setup-all-users.ps1
```

## 用什么工具打开

| 工具 | 怎么用 | 本机状态 |
| --- | --- | --- |
| **本目录自带的离线 HTML** | 双击 `honeymom.html`,无需任何依赖,离线可用 | ✅ 已验证 |
| **Protégé 5.6.9** | 打开 `.ttl` 或 `.owx` 看类树并编辑 | ✅ 已安装 |
| **Python + RDFLib** | `rdflib.Graph().parse("honeymom.ttl", format="turtle")`,可 SPARQL 查询 | ✅ 已装(rdflib 7.6.0) |
| **owlready2** | 可读 OWL/XML;但它的 OWL/XML 方言与 W3C 标准不一致,且推理需 Java | ✅ 已装 0.51 |
| **Apache Jena**(rapper/riot/sparql) | 命令行校验与 SPARQL 查询 | ⬜ 未装 |
| **VS Code** | 装 Turtle/RDF 语法高亮扩展即可当纯文本看 | ⬜ 未装扩展 |

## 规模

75 个类 · 125 个对象属性 · 219 个数据属性 · 0 个实例 · 1765 个三元组 · 135 条图投影边

(OWL API 读出的签名里是 76 个类,多出来的是 `rdfs:Resource` —— 它本身是 OWL 类,
本模型把几个共享属性的 domain 定为 `rdfs:Resource`。)

## 范围

**覆盖** ISA-95 Level 3 运营主干:

- 主数据:工厂 / 车间 / 产线 / 工位 / 物料 / BOM / 工艺路线 / 工艺步骤 / 班次 / 班组 / 员工 / 人员技能 / 换型时间
- 生产执行:生产工单 / 工单工序 / 报工记录 / 领料退料 / 物料齐套 / 在制品 / 零件事件 / 安灯 / 物料申请 / 排程调整建议 / 上下工记录
- 质量:缺陷代码 / 检验模板 / 检验项目 / 检验记录 / 检验值 / 不合格品 / 返修记录 / 首检放行 / 批次冻结 / 量检具 / 校准记录
- 设备:设备台账 / 设备状态记录 / 报警 / 点检保养计划 / 点检保养记录 / 维修工单 / 模具夹具 / 设备停机计划
- 仓储物流:仓库 / 库位 / 库存 / 出入库记录 / 发运记录
- 计划 MRP:需求预测 / 物料计划参数 / MRP 运算 / MRP 建议
- 接口域:客户 / 销售订单 / 订单行 / 交货计划 / 报价单 / 供应商 / 请购单 / 采购订单 / 采购明细 / 系统用户 / 数据源 / 采集点

**不覆盖**(有意排除):财务凭证与成本核算、AI 助手、标签打印、包装发运、委外加工、客诉召回、IATF 受控文件流。

源系统共 141 个实体、1519 个字段、26 个模块;本次按业务主干取其 75 个类。

## 建模依据(不是表结构镜像)

- **结构来源**:`honeymom/schema*.py` 的实体定义。一份定义同时生成数据库表、通用 REST API 和前端表单,
  因此 `E(...)` 里的 `R(字段, 中文名, 目标实体)` 就是业务关联,`EN(..., 枚举)` 就是受控值属性。
  用 `tools/extract_entities.py` 静态抽取(不导入应用,避免依赖 sqlalchemy 与运行时)。
- **语义来源**:`honeymom/services/` 的实际业务规则。本体里的关键注释都指回具体实现:
  - 报工的 7 道放行闸门 → `services/gates.py` `submit_report`
  - 首检放行、批次冻结、返修复检 → `services/gates.py`
  - ECN 停工阻断报工 → `services/exec_doc.py` `report_gate`
  - OEE 三率公式与损失分类 → `services/equipment.py` `oee_of`
  - 排产约束(缺料 / 设备停机 / 无合格操作工 / 模具占用与寿命 / 换型 / 非工作班次)→ `services/scheduling.py`

## 建模取舍

- **枚举单值的,建成互斥子类 + 枚举属性双轨**:物料类型(`mtype`)与检验类型(`itype`)在源码里是单值枚举,
  所以建立了 `owl:disjointWith` 的值划分;其余多值枚举(如设备类型、状态机)只用枚举属性,不硬套子类。
- **数据库约束逐条审过再建模**,不机械映射:`code` 的唯一性只在有业务身份含义的对象上用 `owl:hasKey` 表达;
  系统只读字段、内部流水表不建模。
- **运行时闸门不写成 OWL 公理**:报工放行、冻结拦截这些是代码执行的流程控制,OWL 开放世界语义表达不了
  "现在必须拦住",因此写在 `rdfs:comment` 里说明语义,并明确标注本体不代表可执行约束。
- **函数性属性用 OWL 正规写法**:单值属性声明为 `rdf:type owl:FunctionalProperty`,
  不是 `owl:FunctionalProperty true` —— 后者在 Turtle 里会被解析成"谓词 owl:FunctionalProperty
  取字面量 true",推理器不认,等于白写。(本文件在 OWL/XML 往返校验时发现并修正了这一处,共 18 个属性。)
- **命名空间 `https://example.org/ontology/honeymom#` 是占位符**,上线前需整体替换为真实 IRI。

## 验证结果(按层级,不要混读)

| 层级 | 状态 | 说明 |
| --- | --- | --- |
| Turtle 解析 | ✅ 通过 | rdflib 与 OWL API 两个解析器都无错 |
| 基础结构检查 | ✅ 通过 | 技能脚本 0 warnings:类/属性均有中文 `rdfs:label`,每个属性均有 `rdfs:domain` + `rdfs:range`,无未解析外部引用,无 `file:` IRI,无未展开 `owl:imports` |
| OWL 序列化往返 | ✅ 通过 | `.owx` / `.ofn` / `.omn` / `.rdf` 由官方 OWL API 渲染并回读,**源公理 100% 保留**(只多出内置类型的显式声明) |
| 纯 RDF 序列化往返 | ✅ 通过 | `.jsonld` / `.nt` 回读后与源图逐三元组同构 |
| **OWL 推理(OWL 2 DL)** | ✅ **通过** | Protégé 内置 **HermiT 1.4.1.432**:`isConsistent = true`,本体无不一致公理;推断出 owl:Thing 直接子类 77 个 |
| 浏览器实测 | ✅ 通过 | 离线打开无脚本错误(console 0 条);搜索"报工"过滤出 28/425 命中并正确联动详情;点击实体定位详情与 15 条 domain 反查;缩放/重置正常;三元组分页 2/2 页 ×50 条 |
| 计数一致性 | ✅ 一致 | 页面头部 75/125/219/0/1765 与图脚注"75 个命名类 · 135 条投影边"、三元组"72 / 1765 条"均与 TTL 解析结果吻合;HTML 页脚 SHA-256 与源文件一致 |
| Protégé 图形界面实测 | ⬜ 未执行 | 本会话没有桌面控制工具,无法自动点击 GUI;但 `.owx`/`.ttl` 均由 Protégé 使用的同一套 OWL API 生成与校验 |
| SHACL / 业务约束校验 | ⬜ 未执行 | 业务规则由代码执行,本体未附带 SHACL 形状 |
| Foundry 导入 | ⬜ 未执行 | 本体为 OWL 知识模型,不是 Foundry 原生导出格式,不能直接导入 |

## 重新生成

源系统 schema 变更后:

```bash
# 1. 重新抽取实体模型,核对是否有新增 / 改名
python tools/extract_entities.py --summary
python tools/extract_entities.py --fields work_order,report,ncr

# 2. 改完 honeymom.ttl 后先做语法自查
python tools/_bisect_turtle.py honeymom.ttl

# 3. 一条命令重建全部产物并做一致性校验
python tools/regenerate_all.py
#    (可选参数:技能根目录、Protégé 安装目录;默认读环境里的标准路径)
```

## 建议的下一步

按文章的说法,本体梳理的最后一环是"让熟悉系统的人核对"。建议至少请生产计划、质检、设备三方各过一遍:

1. 报工闸门的 7 条是否与现场实际一致(尤其超计划比例 `report_over_pct` 的口径)。
2. 首检放行的触发场景是否覆盖"换刀/换班"这两个高频切换点。
3. 模具的"同一时间只能在一台设备上"是否在排产里真的作为硬约束执行。
4. 批次冻结的解冻规则是否与实际追溯流程一致。
5. 命名空间占位符替换成贵司真实 IRI(替换后重跑 `regenerate_all.py`)。
