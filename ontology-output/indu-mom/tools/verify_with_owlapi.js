// 用 Protégé 自带的 OWL API + HermiT 校验本体,并导出其它 OWL 序列化。
// 无需单独安装 Java:Protégé 5.6.9 自带 JRE 11 与 Nashorn(jrunscript.exe)。
//
// 关键点:不手写 OWL/XML —— OWL API 4.5 的 OWL/XML 解析器底层是 RDF/XML 解析器,
// 要求 rdf:RDF 根元素,手写格式很容易不被接受(实测直接解析失败)。
// 改用官方渲染器导出,Protégé 用的就是同一套 OWL API,格式天然兼容。
//
// 运行(在 Protege-5.6.9 目录下):
//   $cp = ((Get-ChildItem bundles\*.jar).FullName + (Get-ChildItem plugins\*.jar).FullName +
//          (Get-ChildItem lib-extra\*.jar).FullName) -join ';'
//   .\jre\bin\jrunscript.exe -cp $cp <本脚本路径> [ttl路径] [输出目录]
var File = Java.type("java.io.File");
var IRI = Java.type("org.semanticweb.owlapi.model.IRI");
var OWLManager = Java.type("org.semanticweb.owlapi.apibinding.OWLManager");
var LoaderConf = Java.type("org.semanticweb.owlapi.model.OWLOntologyLoaderConfiguration");

function arg(i, def) {
    try {
        if (typeof arguments !== "undefined" && arguments.length > i && arguments[i]) {
            return arguments[i];
        }
    } catch (e) {}
    return def;
}

var TTL = arg(0, "D:\\pengjun\\my-projects\\Indu-mom\\ontology-output\\indu-mom\\honeymom.ttl");
var OUTDIR = arg(1, "D:\\pengjun\\my-projects\\Indu-mom\\ontology-output\\indu-mom");

function newManager() {
    var mgr = OWLManager.createOWLOntologyManager();
    var conf = new LoaderConf();
    conf.setLoadAnnotationAxioms(true);
    mgr.setOntologyLoaderConfiguration(conf);
    return mgr;
}

function stats(o) {
    return "类=" + o.getClassesInSignature().size()
        + " 对象属性=" + o.getObjectPropertiesInSignature().size()
        + " 数据属性=" + o.getDataPropertiesInSignature().size()
        + " 个体=" + o.getIndividualsInSignature().size()
        + " 公理=" + o.getAxioms().size();
}

var mgr1 = newManager();
print("=== 1. Turtle 解析(OWL API)===");
var ont1 = mgr1.loadOntologyFromOntologyDocument(new File(TTL));
print("    " + stats(ont1));

var FORMATS = [
    ["org.semanticweb.owlapi.formats.OWLXMLDocumentFormat", "honeymom.owx", "OWL/XML"],
    ["org.semanticweb.owlapi.formats.FunctionalSyntaxDocumentFormat", "honeymom.ofn", "Functional Syntax"],
    ["org.semanticweb.owlapi.formats.ManchesterSyntaxDocumentFormat", "honeymom.omn", "Manchester Syntax"],
    ["org.semanticweb.owlapi.formats.RDFXMLDocumentFormat", "honeymom.rdf", "RDF/XML"]
];

print("=== 2. 用官方渲染器导出,并逐个回读比对(公理层)===");
var allKept = true;
for (var i = 0; i < FORMATS.length; i++) {
    var cls = FORMATS[i][0], name = FORMATS[i][1], label = FORMATS[i][2];
    var out = new File(OUTDIR, name);
    try {
        mgr1.saveOntology(ont1, new (Java.type(cls))(), IRI.create(out));
        var m2 = newManager();
        var back = m2.loadOntologyFromOntologyDocument(out);
        var same = ont1.getAxioms().equals(back.getAxioms());
        var onlySrc = new java.util.HashSet(ont1.getAxioms());
        onlySrc.removeAll(new java.util.HashSet(back.getAxioms()));
        var kept = onlySrc.size() === 0;   // 判据:源公理一条都不能丢
        allKept = allKept && kept;
        print("    " + label + "  " + name + "  " + out.length() + " B"
            + "  回读公理=" + back.getAxioms().size()
            + "  源公理全部保留=" + kept
            + "  集合完全相等=" + same);
        if (!kept) {
            print("      丢失 " + onlySrc.size() + " 条:");
            var it = onlySrc.iterator(), n = 0;
            while (it.hasNext() && n < 5) { print("        - " + it.next()); n++; }
        } else if (!same) {
            var onlyBack = new java.util.HashSet(back.getAxioms());
            onlyBack.removeAll(new java.util.HashSet(ont1.getAxioms()));
            print("      多出 " + onlyBack.size() + " 条(为用到的内置类型补出的显式声明):");
            var it2 = onlyBack.iterator(); n = 0;
            while (it2.hasNext() && n < 4) { print("        + " + it2.next()); n++; }
        }
    } catch (e) {
        allKept = false;
        print("    " + label + " 失败: " + e);
    }
}
print("    >>> 全部 OWL 序列化:源公理 100% 保留 = " + allKept);

print("=== 3. HermiT 推理(Protégé 内置)===");
try {
    var HermiTFactory = Java.type("org.semanticweb.HermiT.ReasonerFactory");
    var reasoner = new HermiTFactory().createReasoner(ont1);
    reasoner.flush();
    print("    推理器: " + reasoner.getReasonerName() + " " + reasoner.getReasonerVersion());
    try {
        print("    本体一致性 isConsistent = " + reasoner.isConsistent());
    } catch (e1) { print("    一致性检查跳过: " + e1); }
    try {
        var df = ont1.getOWLOntologyManager().getOWLDataFactory();
        // getSubClasses 返回 NodeSet(不是 Stream),直接遍历
        var ns = reasoner.getSubClasses(df.getOWLThing(), false);
        var n = 0;
        var it = ns.iterator();
        while (it.hasNext()) { it.next(); n++; }
        print("    推断出的 owl:Thing 直接子类数: " + n);
    } catch (e2) { print("    子类推理跳过: " + e2); }
    reasoner.dispose();
} catch (e) {
    print("    推理失败: " + e);
}
print("=== 完成 ===");
