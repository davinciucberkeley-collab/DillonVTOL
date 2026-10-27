// Exports the FEA result fields for the review's 3-D field viewer: for each saved static study (fine mesh) the
// surface mesh, nodal von Mises stress (MPa) and resultant displacement (mm).
// Usage: SimFields.exe cad\sim           -> cad\sim\fields\boom.json, spar.json (gitignored; reduced by analysis/fea_fields.py)
// Reads the studies Sim.cs saved inside cad/sim/FEA_Boom_Arm.SLDPRT and FEA_Spar_Joiner.SLDPRT; a study whose results
// are not loaded is run again (same mesh and loads, so the same answer). The documents are closed without saving.
using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Globalization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.cosworks;

class SimFields
{
    static readonly CultureInfo IC = CultureInfo.InvariantCulture;
    static SldWorks sw; static CosmosWorks cw; static string Out;
    static void Log(string s) { Console.WriteLine(s); }

    static int Main(string[] a)
    {
        Out = Path.GetFullPath(a[0]); Directory.CreateDirectory(Path.Combine(Out, "fields"));
        sw = (SldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application"));
        sw.Visible = true;
        // the add-in loads by its DLL path and can take a while after SOLIDWORKS starts (as cad/Sim.cs)
        const string ADDIN = @"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\Simulation\cosworks.dll";
        sw.LoadAddIn(ADDIN); object cb = sw.GetAddInObject("SldWorks.Simulation");
        for (int i = 0; i < 30 && cb == null; i++) { System.Threading.Thread.Sleep(3000); sw.LoadAddIn(ADDIN); cb = sw.GetAddInObject("SldWorks.Simulation"); Log("waiting for the Simulation add-in"); }
        if (cb == null) { Log("Simulation add-in unavailable"); return 1; }
        cw = ((CwAddincallback)cb).CosmosWorks;
        Export("FEA_Boom_Arm.SLDPRT", "Boom full thrust fine mesh", "boom");
        Export("FEA_Spar_Joiner.SLDPRT", "Spar ultimate load fine mesh", "spar");
        return 0;
    }

    static void Export(string file, string study, string name)
    {
        int e = 0, w = 0;
        ModelDoc2 d = sw.OpenDoc6(Path.Combine(Out, file), (int)swDocumentTypes_e.swDocPART, (int)swOpenDocOptions_e.swOpenDocOptions_Silent, "", ref e, ref w);
        if (d == null) { Log("open failed " + file + " " + e); return; }
        sw.ActivateDoc3(d.GetTitle(), false, 0, ref e);
        CWStudyManager sm = cw.ActiveDoc.StudyManager; CWStudy st = null;
        for (int i = 0; i < sm.StudyCount; i++) { CWStudy s = sm.GetStudy(i); if (s.Name == study) { st = s; sm.ActiveStudy = i; } }
        if (st == null) { Log("study not found: " + study); sw.CloseDoc(d.GetTitle()); return; }
        if (st.Results == null) { Log(study + ": results not loaded, running"); int r = st.RunAnalysis(); if (r != 0) { Log("analysis failed " + r); return; } }
        // nodal results: GetStress(0 = all nodes) returns one row per node [node, components...]; the von Mises column is
        // the one whose maximum matches SOLIDWORKS' own GetMinMaxStress(9 = VON) - checked, not assumed
        int nn = st.Mesh.NodeCount;
        double vmax = Convert.ToDouble(((object[])st.Results.GetMinMaxStress(9, 0, 1, null, 0, out e))[3]);
        double[] sa = ToD(st.Results.GetStress(0, 1, null, 0, out e));
        int ss = nn > 0 && sa.Length % nn == 0 ? sa.Length / nn : 0; int col = -1;
        Log(study + ": GetStress " + sa.Length + " values, stride " + ss + ", SOLIDWORKS max von Mises " + (vmax / 1e6).ToString("F2", IC) + " MPa");
        for (int c = 1; c < ss && col < 0; c++)
        {
            double mx = 0; for (int r = 0; r + ss <= sa.Length; r += ss) mx = Math.Max(mx, sa[r + c]);
            if (Math.Abs(mx - vmax) <= 0.01 * vmax) col = c;
        }
        if (col < 0) { Log("no column matches the von Mises maximum: not exported"); sw.CloseDoc(d.GetTitle()); return; }
        var von = new Dictionary<int, double>(); for (int r = 0; r + ss <= sa.Length; r += ss) von[(int)sa[r]] = sa[r + col] * 1e-6;
        // displacement magnitude from [node, ux, uy, uz, ...] in metres (units 2; cad/Sim.cs multiplies by 1000), checked against GetMinMaxDisplacement(3 = URES); analysis/fea_fields.py converts to mm
        double dmax = Convert.ToDouble(((object[])st.Results.GetMinMaxDisplacement(3, 1, null, 2, out e))[3]);
        double[] da = ToD(st.Results.GetTranslationalDisplacement(1, null, 2, out e));
        int ds = nn > 0 && da.Length % nn == 0 ? da.Length / nn : 4; var dis = new Dictionary<int, double>(); double dm = 0;
        for (int r = 0; r + ds <= da.Length; r += ds) { double u = Math.Sqrt(da[r + 1] * da[r + 1] + da[r + 2] * da[r + 2] + da[r + 3] * da[r + 3]); dis[(int)da[r]] = u; dm = Math.Max(dm, u); }
        Log("  von Mises column " + col + "; displacement max " + dm.ToString("F3", IC) + " mm vs SOLIDWORKS " + dmax.ToString("F3", IC) + " mm");
        WriteField(name, st, new Dictionary<string, Dictionary<int, double>> { { "von_MPa", von }, { "disp_mm", dis } });
        sw.CloseDoc(d.GetTitle());   // closed without saving
    }

    // rows of [node, values...] of any stride: the first value after the node number, or the last one (URES closes
    // the displacement row [node, ux, uy, uz, ures]), scaled by k
    static Dictionary<int, double> PerNode(double[] a, int nn, double k, bool last)
    {
        var m = new Dictionary<int, double>(); if (a.Length == 0) return m;
        int stride = nn > 0 && a.Length % nn == 0 ? a.Length / nn : 2;
        for (int i = 0; i + stride <= a.Length; i += stride) m[(int)a[i]] = a[last ? i + stride - 1 : i + 1] * k;
        Log("  rows " + (a.Length / stride) + ", stride " + stride);
        return m;
    }

    static double[] ToD(object o)
    {
        if (o == null || o is DBNull) return new double[0];
        if (o is double[]) return (double[])o;
        if (o is float[]) { float[] fa = (float[])o; var rf = new double[fa.Length]; for (int i = 0; i < fa.Length; i++) rf[i] = fa[i]; return rf; }
        if (!(o is object[])) return new double[0];
        object[] arr = (object[])o; var r = new double[arr.Length]; for (int i = 0; i < arr.Length; i++) r[i] = Convert.ToDouble(arr[i]); return r;
    }

    // the same surface extraction as cad/Thermal.cs: tet faces used once are on the outside
    static void WriteField(string name, CWStudy st, Dictionary<string, Dictionary<int, double>> fields)
    {
        double[] a = ToD(st.Mesh.GetNodes()); int n = a.Length / 4; var ids = new int[n]; var xyz = new double[3 * n];
        for (int i = 0; i < n; i++) { ids[i] = (int)a[4 * i]; xyz[3 * i] = a[4 * i + 1]; xyz[3 * i + 1] = a[4 * i + 2]; xyz[3 * i + 2] = a[4 * i + 3]; }
        var idx = new Dictionary<int, int>(); for (int i = 0; i < n; i++) idx[ids[i]] = i;
        double[] ed = ToD(st.Mesh.GetElements()); int ne = st.Mesh.ElementCount, stride = ne > 0 && ed.Length % ne == 0 ? ed.Length / ne : 16;
        var faces = new Dictionary<string, int[]>(); int[][] tf = { new[] { 0, 1, 2 }, new[] { 0, 1, 3 }, new[] { 1, 2, 3 }, new[] { 0, 2, 3 } };
        for (int e = 0; e + stride <= ed.Length; e += stride)
        {
            int[] c = { (int)ed[e + 1], (int)ed[e + 2], (int)ed[e + 3], (int)ed[e + 4] };
            foreach (int[] f in tf)
            {
                int[] t = { c[f[0]], c[f[1]], c[f[2]] }; Array.Sort(t); string k = t[0] + "," + t[1] + "," + t[2];
                if (faces.ContainsKey(k)) faces[k][3]++; else faces[k] = new[] { c[f[0]], c[f[1]], c[f[2]], 1 };
            }
        }
        var sb = new StringBuilder(); sb.Append("{\"name\":\"" + name + "\",\"nodes\":[");
        for (int i = 0; i < n; i++) { if (i > 0) sb.Append(','); sb.Append(xyz[3 * i].ToString("G6", IC)).Append(',').Append(xyz[3 * i + 1].ToString("G6", IC)).Append(',').Append(xyz[3 * i + 2].ToString("G6", IC)); }
        sb.Append("],\"tris\":["); bool first = true; int nt = 0;
        foreach (var kv in faces) if (kv.Value[3] == 1 && idx.ContainsKey(kv.Value[0]) && idx.ContainsKey(kv.Value[1]) && idx.ContainsKey(kv.Value[2]))
            { if (!first) sb.Append(','); first = false; sb.Append(idx[kv.Value[0]]).Append(',').Append(idx[kv.Value[1]]).Append(',').Append(idx[kv.Value[2]]); nt++; }
        sb.Append("],\"fields\":{"); bool f1 = true;
        foreach (var kv in fields)
        {
            if (!f1) sb.Append(','); f1 = false; sb.Append("\"" + kv.Key + "\":[");
            for (int i = 0; i < n; i++) { if (i > 0) sb.Append(','); double v; sb.Append(kv.Value.TryGetValue(ids[i], out v) ? v.ToString("G5", IC) : "null"); }
            sb.Append(']');
        }
        sb.Append("}}");
        File.WriteAllText(Path.Combine(Out, "fields", name + ".json"), sb.ToString());
        Log("field " + name + ": " + n + " nodes, " + nt + " surface triangles, element stride " + stride + ", von Mises nodes " + fields["von_MPa"].Count);
    }
}
