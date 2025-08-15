import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import TopNav from "@/components/TopNav";
import Seo from "@/components/Seo";
import { FloatingChatbot } from "@/components/FloatingChatbot";
import { ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { APIService } from "../services/api.service";

/**
 * 从 final_synthesis 中提取指定序号的部分内容
 * @param text 完整的 final_synthesis 文本
 * @param sectionNumber 要提取的部分序号 (2, 4, 5)
 * @returns 对应部分的正文字符串（去掉标题）
 */
function extractSection(text: string, sectionNumber: number): string {
  if (!text || typeof text !== "string") return "";

  // 匹配 **2. ... 到下一个 **3. ... 或文末
  const regex = new RegExp(
    `\\*\\*${sectionNumber}\\.\\s[\\s\\S]*?(?=\\n\\n\\*\\*${sectionNumber + 1}\\.\\s|\\n\\n\\*\\*${sectionNumber + 2}\\.\\s|$)`,
    "i"
  );

  const match = text.match(regex);
  if (match) {
    // 去掉 "**2. ..." 标题
    return match[0]
      .replace(new RegExp(`^\\*\\*${sectionNumber}\\..*?\\*\\*`), "")
      .trim();
  }

  return "";
}


function parseFinalSynthesis(synthesis?: string) {
  if (!synthesis) return [];
  const sections = synthesis.split(/##\s+/).filter(Boolean);
  return sections.map(sec => {
    const [titleLine, ...rest] = sec.split("\n");
    return {
      title: titleLine.trim(),
      content: rest.join("\n").trim()
    };
  });
}


const mock = {
  acme: {
    name: "Acme Bank Holdings",
    score: 86,
    summary: "该公司的可持续发展报告存在高风险，主要集中在模糊声明和缺乏第三方验证。",
    breakdown: [
      { type: "模糊声明", value: 85 },
      { type: "缺乏指标", value: 72 },
      { type: "误导性术语", value: 68 },
      { type: "第三方验证不足", value: 74 },
      { type: "范围界定不清", value: 61 },
    ],
    evidence: {
      模糊声明: [
        {
          quote: "我们致力于未来实现碳中和。",
          why: "缺少时间表与量化指标，属于非具体、不可验证的表述。",
        },
      ],
      缺乏指标: [
        {
          quote: "已显著降低供应链排放。",
          why: "未提供基线年、降低幅度、覆盖范围等具体数据。",
        },
      ],
    },
    external: [
      "监管快讯：某机构正在审查其环境声明合规性。",
      "行业新闻：多家银行更新其披露标准以满足最新监管。",
    ],
  },
};

const riskTone = (score: number) => {
  if (score >= 70) return "destructive";  // 高风险 - 红色
  if (score >= 40) return "accent";       // 中风险 - 蓝色
  return "secondary";                      // 低风险 - 灰色
};

const Company = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const mockData = (mock as any)[id ?? "acme"] ?? (mock as any).acme;

  const { data: apiRes } = useQuery({
    queryKey: ["report", id],
    queryFn: async () => {
      if (!id) throw new Error("missing id");
      // const res = await fetch(`/v1/report/${id}`);
      // if (!res.ok) throw new Error("report not found");
      // return res.json();
      return await APIService.getReport(id);
    },
    enabled: !!id,
    retry: 0,
  });

  const viewLS = (() => {
    try {
      if (!id) return null;
      const raw = localStorage.getItem(`report:${id}`);
      if (!raw) return null;
      const d = JSON.parse(raw);
      return {
        name: d.company_name || "Unknown Company",
        score: Math.round(d.overall_score ?? 0),
        summary: d.summary ?? "",
        breakdown: (d.breakdown ?? []).map((x: any) => ({ type: x.type, value: Math.round(x.value ?? 0) })),
        evidenceGroups: d.evidence ?? [],
        final_synthesis: d.final_synthesis ?? d.response ?? "",
        external: d.external ?? [],
      };
    } catch {
      return null;
    }
  })();

const view = apiRes?.data
  ? {
      name: apiRes.data.company_name,
      final_synthesis: apiRes.data.final_synthesis ?? apiRes.data.response ?? "",
      // 总体评分
      score: (() => {
        try {
          if (apiRes.data.graphdata) {
            let graphdata = apiRes.data.graphdata;
            if (typeof graphdata === 'string') {
              let cleanData = graphdata.replace(/```json\n?/g, '').replace(/```/g, '').trim();
              try {
                graphdata = JSON.parse(cleanData);
              } catch {
                cleanData = cleanData.replace(/^\s*{\s*/, '{').replace(/\s*}\s*$/, '}');
                graphdata = JSON.parse(cleanData);
              }
            }
            const overallScore = graphdata.overall_greenwashing_score?.score ?? 0;
            return Math.round(overallScore * 10);
          }
          return Math.round(apiRes.data.overall_score ?? 0);
        } catch (e) {
          console.error('Failed to parse graphdata:', e);
          return Math.round(apiRes.data.overall_score ?? 0);
        }
      })(),
      // 执行摘要
      summary: (() => {
        if (apiRes.data.final_synthesis) {
          const synthesis = apiRes.data.final_synthesis;
          const execSummaryMatch = synthesis.match(
            /\*\*1\. Executive Summary\*\*([\s\S]*?)(?=\n\n\*\*2\.)/
          );
          if (execSummaryMatch) {
            return execSummaryMatch[1].trim(); // 不截断
          }
          return synthesis.substring(0, 200) + "...";
        }
        return apiRes.data.summary ?? "暂无摘要信息";
      })(),
      // 风险分解
      breakdown: (() => {
        try {
          if (apiRes.data.graphdata) {
            let graphdata = apiRes.data.graphdata;
            if (typeof graphdata === 'string') {
              let cleanData = graphdata.replace(/```json\n?/g, '').replace(/```/g, '').trim();
              try {
                graphdata = JSON.parse(cleanData);
              } catch {
                cleanData = cleanData.replace(/^\s*{\s*/, '{').replace(/\s*}\s*$/, '}');
                graphdata = JSON.parse(cleanData);
              }
            }
            return Object.entries(graphdata)
              .filter(([key]) => key !== 'overall_greenwashing_score')
              .map(([key, value]: [string, any]) => ({
                type: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                value: Math.round((value?.score ?? 0) * 10)
              }));
          }
          return (apiRes.data.breakdown ?? []).map((d: any) => ({
            type: d.type,
            value: Math.round(d.value ?? 0)
          }));
        } catch (e) {
          console.error('Failed to parse breakdown data:', e);
          return [];
        }
      })(),
      // 证据链（第 2 部分）
      evidenceGroups: (() => {
        const sec2 = extractSection(apiRes.data.final_synthesis ?? "", 2);
        return sec2
          ? [{
              type: "Key Findings and Evidence from Document Analysis",
              items: [{ quote: sec2.trim(), why: "" }]
            }]
          : [];
      })(),
      // 外部验证（第 4 部分）
      external: (() => {
        const sec4 = extractSection(apiRes.data.final_synthesis ?? "", 4);
        return sec4 ? [sec4.trim()] : [];
      })(),
      // 建议步骤（第 5 部分）
      recommendedSteps: (() => {
        const sec5 = extractSection(apiRes.data.final_synthesis ?? "", 5);
        return sec5 ? sec5.trim() : "";
      })(),
    }
  : viewLS ?? { ...mockData, evidenceGroups: null };


  // 添加调试信息
  console.log('Processed view data:', view);
  console.log("Final synthesis raw:", view.final_synthesis);
  console.log('Score:', view.score);
  console.log('Breakdown:', view.breakdown);
  console.log('Evidence groups:', view.evidenceGroups);
  console.log('External:', view.external);

  const reportSections = parseFinalSynthesis(view.final_synthesis);


  // 测试模式：使用模拟数据覆盖 API 响应
  const TEST_MODE = false; // 设置为 true 启用测试模式
  const testData = {
    company_name: "SGR Fund",
    session_id: "test_session",
    final_synthesis: `## ESG Greenwashing Assessment Report

**Date:** October 27, 2023

**1. Executive Summary**

This report assesses the potential for greenwashing within the ESG-related disclosures of the SGR fund, based on a review of provided documentation. The analysis reveals several areas of concern, ranging from vague language and unsubstantiated claims to a lack of alignment with established sustainability standards. The overall greenwashing score is **8/10**, indicating a high likelihood of misleading or exaggerated sustainability claims. This score reflects significant concerns regarding the transparency, credibility, and impact of the fund's ESG practices. Further investigation and verification are strongly recommended to confirm the extent of greenwashing and to ensure compliance with regulatory requirements and ethical standards.

**2. Key Findings and Evidence from Document Analysis**

The following sections detail the key ESG claims identified in the provided documents, along with an assessment of their potential for greenwashing, external verification results, and recommendations for further investigation.

**2.1. Quotation:** prodotti classificati come ex art. 8 o 9 ai sensi del SFDR, nella Relazione di Gestione è inserito specifico allegato sulla sostenibilità che riporta la misura secondo la quale le caratteristiche ambientali o sociali sono conseguite rispetto a tale prodotto;

**2.2. Explanation:** While claiming compliance with SFDR Article 8 or 9 suggests a commitment to sustainability, the statement remains vague. The "specific annex" reporting on the "extent to which environmental or social characteristics are achieved" lacks quantifiable metrics and concrete examples. The term "misura" (measure) is also vague. The news validation tool flagged "Benchmark" as not being in the whitelist, and the Wikirate validation tool also flagged "Benchmark" as not being in the whitelist. **Revised Explanation:** The initial assessment remains valid. The lack of specific, measurable, achievable, relevant, and time-bound (SMART) metrics in the sustainability annex raises concerns about the fund's ability to demonstrate genuine progress towards its stated environmental and social objectives. The absence of a clear benchmark for performance further exacerbates this issue.

**2.3. Greenwashing_Likelihood_Score:** 6 (Revised to **7** based on validation results. The lack of readily available information to validate the claims increases the likelihood of greenwashing.)

**2.4. External Verification Conducted and Verification Results:**

*   **News Validation:** [Warning] 'Benchmark' not in whitelist. Forced news validation.
*   **Wikirate Validation:** [Warning] 'Benchmark' not in whitelist. Forced Wikirate validation.

The validation tools were unable to provide conclusive evidence due to the lack of specific keywords and the general nature of the claim.

**2.5. Further Verification Required:** Review the "specific annex" mentioned in the report. Analyze the metrics used to measure the achievement of environmental or social characteristics. Check if these metrics are aligned with SFDR requirements and industry best practices. Compare the fund's performance against its stated objectives and benchmarks. **Additional External Verification Required:** Obtain independent third-party assurance of the sustainability annex and its contents. This would provide an objective assessment of the fund's ESG performance and credibility.

**2.1. Quotation:** relativamente alla composizione del portafoglio si rinvia alla Parte B - Le att ività, le passività e il valore complessivo netto - Sezione II - Le attività - della Nota Integrativa della presente Relazione di Gestione ed in particolare, tra le altre, ai prospetti relativi ai Settori economici di impiego delle risorse del Fondo, al Prospetto di dettaglio dei principali titoli i n portafoglio (i primi 50 e comunque tutti quelli che superano lo 0,5% delle attività del Fondo) ed alle tabelle successive degli strumenti finanziari quotati, non quotati, titoli di debito, strumenti finanziari derivati;

**2.2. Explanation:** Referring to other sections of the report for portfolio composition details is standard practice, but it can obscure the true nature of the investments. While providing a list of top 50 holdings or those exceeding 0.5% seems transparent, it might exclude a significant portion of the portfolio, potentially hiding investments in less sustainable or controversial sectors. The mention of 'strumenti finanziari derivati' (derivative financial instruments) also raises concerns. **Revised Explanation:** The news validation tool found no relevant news articles. The Wikirate validation tool provided an assessment of each claim based on the provided Wikirate database data. The initial assessment remains valid. The limited disclosure of portfolio holdings and the potential use of complex derivative instruments warrant further scrutiny to ensure transparency and prevent the concealment of unsustainable investments.

**2.3. Greenwashing_Likelihood_Score:** 5 (Revised to **6** based on validation results. The lack of readily available information to validate the claims increases the likelihood of greenwashing.)

**2.4. External Verification Conducted and Verification Results:**

*   **News Validation:** No relevant news articles found for this company
*   **Wikirate Validation:** Here's an assessment of each claim based on the provided Wikirate database data:

The validation tools were unable to provide conclusive evidence due to the lack of specific keywords and the general nature of the claim.

**2.5. Further Verification Required:** Analyze the complete portfolio composition, not just the top holdings. Assess the ESG performance of all underlying investments, including those held through derivative instruments. Calculate the weighted average ESG score of the entire portfolio and compare it to the fund's stated sustainability objectives. **Additional External Verification Required:** Compare the fund's portfolio composition to that of similar ESG funds to identify any significant discrepancies or outliers.

**2.1. Quotation:** Per i rimanenti 1 0 fondi, in ogni caso, la SGR applica uno screening negativo di base che prevede specifici criteri di esclusione, al ricorrere dei quali la stessa si obbliga a non effettuare un investimento ove appunto l'investimento target rientri nelle categorie escluse in quanto non virtuose sotto il profilo ESG.

**2.2. Explanation:** The statement describes a "negative screening" approach, which excludes investments based on certain criteria. While this is a common ESG practice, it can be a form of greenwashing if the exclusion criteria are weak or narrowly defined. The phrase "non virtuose sotto il profilo ESG" (not virtuous from an ESG perspective) is vague and subjective. **Revised Explanation:** The news validation tool returned an error. The Wikirate validation tool provided an assessment of each claim based on the provided Wikirate database data. The initial assessment remains valid. The lack of transparency regarding the specific exclusion criteria and the subjective nature of the "non virtuose" definition raise significant concerns about the effectiveness and credibility of the negative screening process.

**2.3. Greenwashing_Likelihood_Score:** 7 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **News Validation:** [Error] Missing news result.
*   **Wikirate Validation:** **1. Claim:** prodotti classificati come ex art. 8 o 9 ai sensi del SFDR, nella Relazione di Gestione è inserito specifico allegato sulla sostenibilità che riporta la misura secondo la quale le caratteristiche ambientali o sociali sono conseguite rispetto a tale prodotto;

The validation tools were unable to provide conclusive evidence due to the lack of specific keywords and the general nature of the claim.

**2.5. Further Verification Required:** Obtain a detailed list of the "specific criteria di esclusione" (specific exclusion criteria). Assess the stringency of these criteria and compare them to industry best practices. Analyze the fund's portfolio to ensure that it adheres to the stated exclusion criteria. Check for any investments that appear to violate the exclusion criteria. **Additional External Verification Required:** Benchmark the fund's exclusion criteria against those of leading ESG funds and industry standards to assess its relative stringency.

**2.1. Quotation:** La SGR prende in considerazione gli effetti negativi delle decisioni di investimento sui fattori di sostenibilità ai sensi dell'articolo 4 del Regolamento (UE) 2019/2088 del Parlamento europeo e del Consiglio del 27 novembre 2019.

**2.2. Explanation:** Stating that the SGR "takes into consideration" the negative impacts of investment decisions on sustainability factors, as required by SFDR Article 4, is a minimal commitment. It doesn't necessarily mean that the SGR actively avoids or mitigates these negative impacts. The phrase "takes into consideration" is weak and lacks concrete action. **Revised Explanation:** The initial assessment remains valid. This statement is a compliance statement that doesn't guarantee meaningful ESG integration.

**2.3. Greenwashing_Likelihood_Score:** 6 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **None**

**2.5. Further Verification Required:** Request documentation on how the SGR "takes into consideration" negative sustainability impacts. Assess the processes and methodologies used to identify, assess, and mitigate these impacts. Check for evidence of concrete actions taken to reduce negative impacts, such as engagement with investee companies or divestment from unsustainable activities. **Additional External Verification Required:** Interview the SGR's investment team to understand how ESG considerations are integrated into their decision-making process and how they address potential negative impacts.

**2.1. Quotation:** Gli investimenti del Fondo non hanno tenuto conto dei criteri dell'UE per le attività economiche ecosostenibili.

**2.2. Explanation:** This statement is a direct admission that the fund's investments do not align with the EU Taxonomy for sustainable activities. While transparency is appreciated, it raises serious questions about the fund's overall sustainability claims. **Revised Explanation:** The initial assessment remains valid. This is a significant red flag.

**2.3. Greenwashing_Likelihood_Score:** 8 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **None**

**2.5. Further Verification Required:** N/A - The statement is self-explanatory.

**2.1. Quotation:** Al Fondo sono stati applicati i criteri generali previsti dalla Politica di Sostenibilità per tutti i fondi gestiti dalla SGR che prevedono l'esclusione di emittenti societari che: a. derivano parte non residuale del loro fatturato dalla produzione di armamenti non convenzionali (quali le armi nucleari);

**2.2. Explanation:** Excluding companies deriving a "non residual" part of their revenue from unconventional weapons (like nuclear weapons) is a weak exclusion criterion. The term "non residual" is ambiguous and allows for investments in companies that are significantly involved in the production of such weapons, as long as it's not the *majority* of their revenue. **Revised Explanation:** The news validation tool returned an error. The Wikirate validation tool provided an assessment of each claim based on the provided Wikirate database data. The initial assessment remains valid. The ambiguity of "non residual" significantly weakens the exclusion criterion and raises concerns about the fund's commitment to ethical investing.

**2.3. Greenwashing_Likelihood_Score:** 6 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **News Validation:** [Error] Missing news result.
*   **Wikirate Validation:** *   **Status**: Not Mentioned
    *   **Reasoning**: The Wikirate data provides no information about SFDR classification, sustainability annexes, or the measurement of environmental/social characteristics.
    *   **news_quotation**: N/A

The validation tools were unable to provide conclusive evidence due to the lack of specific keywords and the general nature of the claim.

**2.5. Further Verification Required:** Obtain the full "Politica di Sostenibilità" (Sustainability Policy) and analyze the definition of "non residual". Determine the threshold for revenue derived from unconventional weapons that would trigger exclusion. Analyze the fund's portfolio to identify any investments in companies involved in the production of such weapons and assess whether they comply with the "non residual" threshold. **Additional External Verification Required:** Compare the fund's exclusion criteria for controversial weapons to those of leading ethical investment funds to assess its relative stringency.

**2.1. Quotation:** a.5) si rappresenta che la SGR ai fini dell'esercizio delle attività di impegno previste nella propria Politica di Impegno nel corso dell'anno 2023 non si è avvalsa di consulenti in materia di voto e non ha adottato una politica di concessione di titoli in prestito per perseguire le attività di engagement;

**2.2. Explanation:** The SGR did not use voting advisors or securities lending to pursue engagement activities. While not inherently greenwashing, it raises questions about the effectiveness of their engagement strategy. **Revised Explanation:** The news validation tool returned an error. The Wikirate validation tool provided an assessment of each claim based on the provided Wikirate database data. The initial assessment remains valid. The lack of these tools may limit the SGR's ability to effectively influence investee companies on ESG issues.

**2.3. Greenwashing_Likelihood_Score:** 6 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **News Validation:** [Error] Missing news result.
*   **Wikirate Validation:** **2. Claim:** relativamente alla composizione del portafoglio si rinvia alla Parte B - Le att ività, le passività e il valore complessivo netto - Sezione II - Le attività - della Nota Integrativa della presente Relazione di Gestione ed in particolare, tra le altre, ai prospetti relativi ai Settori economici di impiego delle risorse del Fondo, al Prospetto di dettaglio dei principali titoli i n portafoglio (i primi 50 e comunque tutti quelli che superano lo 0,5% delle attività del Fondo) ed alle tabelle successive degli strumenti finanziari quotati, non quotati, titoli di debito, strumenti finanziari derivati;

The validation tools were unable to provide conclusive evidence due to the lack of specific keywords and the general nature of the claim.

**2.5. Further Verification Required:** Request details on the SGR's engagement activities with investee companies. Assess the frequency, scope, and outcomes of these engagements. Compare the SGR's engagement strategy to industry best practices and assess its effectiveness. **Additional External Verification Required:** Interview the SGR's engagement team to understand their approach to influencing investee companies and the metrics they use to measure the success of their engagement efforts.

**2.1. Quotation:** b) la SGR investe prevalentemente in titoli azionari quotati; in ogni caso la SGR tiene altresì conto dei risultati non finanziari degli Emittenti Partecipati ai sensi dei principi e dei criteri contenuti nella propria Politica di Sostenibilità, come altresì

**2.2. Explanation:** Investing "prevalentemente" (mainly) in listed equities doesn't preclude investments in other asset classes that may be less sustainable. The phrase "tiene altresì conto dei risultati non finanziari" (also takes into account non-financial results) is vague. **Revised Explanation:** The initial assessment remains valid. The lack of specificity raises concerns about the depth and sincerity of the SGR's ESG integration.

**2.3. Greenwashing_Likelihood_Score:** 5 (No change based on validation results.)

**2.4. External Verification Conducted and Verification Results:**

*   **None**

**2.5. Further Verification Required:** Request details on how the SGR integrates non-financial (ESG) factors into its investment decision-making process. Assess the weighting and importance given to ESG factors relative to financial factors. Check for evidence of how ESG considerations influence portfolio construction and investment selection. **Additional External Verification Required:** Review the SGR's investment mandates and guidelines to determine the extent to which ESG factors are explicitly incorporated into the investment decision-making process.

**3. Greenwashing Types, Likelihood, and Overall Score**

Based on the document analysis, the following greenwashing types are identified, along with an assessment of their likelihood:

*   **Vague or unsubstantiated claims (Score: 8):** High likelihood. The use of ambiguous language, such as "non residual" and "takes into consideration," makes it difficult to assess the true impact of the fund's ESG practices.
*   **Lack of specific metrics or targets (Score: 9):** Very High likelihood. The absence of quantifiable metrics and targets in the sustainability annex and other disclosures raises concerns about the fund's ability to demonstrate genuine progress towards its stated environmental and social objectives.
*   **Misleading terminology (Score: 7):** High likelihood. The use of terms like "non virtuose sotto il profilo ESG" without clear definitions can be misleading and obscure the true nature of the fund's investment decisions.
*   **Cherry-picked data (Score: 5):** Moderate likelihood. The focus on top 50 holdings may exclude a significant portion of the portfolio, potentially hiding investments in less sustainable or controversial sectors.
*   **Absence of third-party verification (Score: 6):** Moderate to High likelihood. The lack of independent third-party assurance of the fund's ESG performance raises concerns about the credibility and objectivity of its sustainability claims.

**Overall Greenwashing Score: 8/10**

**4. Specific Recommendations for Stakeholders**

*   **Investors:** Conduct thorough due diligence before investing in the fund. Request detailed information on the fund's ESG policies, exclusion criteria, and engagement activities. Compare the fund's performance to that of similar ESG funds and industry benchmarks.
*   **Regulators:** Scrutinize the fund's compliance with SFDR and other relevant regulations. Investigate the use of vague language and unsubstantiated claims in the fund's disclosures.
*   **SGR Management:** Enhance the transparency and credibility of the fund's ESG practices. Develop clear and measurable ESG targets, and obtain independent third-party assurance of the fund's sustainability performance.
*   **ESG Rating Agencies:** Incorporate the identified greenwashing risks into the fund's ESG rating. Provide investors with a clear and objective assessment of the fund's sustainability performance.

**5. Risk Assessment and Concerns**

The identified greenwashing risks pose several potential concerns:

*   **Reputational damage:** The fund's reputation could be damaged if it is found to be engaging in greenwashing.
*   **Financial losses:** Investors could suffer financial losses if the fund's ESG performance does not meet their expectations.
*   **Regulatory scrutiny:** The fund could face regulatory scrutiny and penalties if it is found to be in violation of SFDR or other relevant regulations.
*   **Erosion of trust:** Greenwashing can erode trust in the ESG investing industry as a whole.

It is crucial to address these risks by implementing the recommendations outlined in this report and by continuously monitoring the fund's ESG performance and disclosures.`,
    graphdata: `{"Vague or unsubstantiated claims": {"score": 8}, "Lack of specific metrics or targets": {"score": 9}, "Misleading terminology": {"score": 7}, "Cherry-picked data": {"score": 5}, "Absence of third-party verification": {"score": 6}, "overall_greenwashing_score": {"score": 8}}`,
    document_analysis: [
      [
        {
          quotation: "prodotti classificati come ex art. 8 o 9 ai sensi del SFDR, nella Relazione di Gestione è inserito specifico allegato sulla sostenibilità che riporta la misura secondo la quale le caratteristiche ambientali o sociali sono conseguite rispetto a tale prodotto;",
          explanation: "While claiming compliance with SFDR Article 8 or 9 suggests a commitment to sustainability, the statement remains vague. The \"specific annex\" reporting on the \"extent to which environmental or social characteristics are achieved\" lacks quantifiable metrics and concrete examples. The term \"misura\" (measure) is also vague."
        },
        {
          quotation: "relativamente alla composizione del portafoglio si rinvia alla Parte B - Le att ività, le passività e il valore complessivo netto - Sezione II - Le attività - della Nota Integrativa della presente Relazione di Gestione ed in particolare, tra le altre, ai prospetti relativi ai Settori economici di impiego delle risorse del Fondo, al Prospetto di dettaglio dei principali titoli i n portafoglio (i primi 50 e comunque tutti quelli che superano lo 0,5% delle attività del Fondo) ed alle tabelle successive degli strumenti finanziari quotati, non quotati, titoli di debito, strumenti finanziari derivati;",
          explanation: "Referring to other sections of the report for portfolio composition details is standard practice, but it can obscure the true nature of the investments. While providing a list of top 50 holdings or those exceeding 0.5% seems transparent, it might exclude a significant portion of the portfolio, potentially hiding investments in less sustainable or controversial sectors."
        },
        {
          quotation: "Per i rimanenti 1 0 fondi, in ogni caso, la SGR applica uno screening negativo di base che prevede specifici criteri di esclusione, al ricorrere dei quali la stessa si obbliga a non effettuare un investimento ove appunto l'investimento target rientri nelle categorie escluse in quanto non virtuose sotto il profilo ESG.",
          explanation: "The statement describes a \"negative screening\" approach, which excludes investments based on certain criteria. While this is a common ESG practice, it can be a form of greenwashing if the exclusion criteria are weak or narrowly defined. The phrase \"non virtuose sotto il profilo ESG\" (not virtuous from an ESG perspective) is vague and subjective."
        }
      ]
    ],
    news_validation: "News validation found several warnings about 'Benchmark' not being in the whitelist. Forced news validation was required for multiple claims.",
    wikirate_validation: "Wikirate validation provided assessments based on database data, but many claims lacked specific keywords for conclusive verification."
  };

  // 如果启用测试模式，使用测试数据覆盖 API 响应
  if (TEST_MODE && !apiRes?.data) {
    console.log('🔧 测试模式已启用，使用模拟数据');
    const mockApiRes = { data: testData };
    
    // 重新计算 view 对象
    const testView = {
      name: testData.company_name,
      final_synthesis: testData.final_synthesis,
      score: (() => {
        try {
          if (testData.graphdata) {
            let graphdata = typeof testData.graphdata === 'string' 
              ? JSON.parse(testData.graphdata) 
              : testData.graphdata;
            const overallScore = graphdata.overall_greenwashing_score?.score ?? 0;
            return Math.round(overallScore * 10); // 转换为 0-100 范围
          }
          return 0;
        } catch (e) {
          console.error('Failed to parse test graphdata:', e);
          return 0;
        }
      })(),
      summary: (() => {
        if (testData.final_synthesis) {
          const synthesis = testData.final_synthesis;
          const execSummaryMatch = synthesis.match(/## ESG Greenwashing Assessment Report\s*\n\n\*\*1\. Executive Summary\*\*\s*\n\n([\s\S]*?)(?=\n\n\*\*2\.|$)/);
          if (execSummaryMatch) {
            const summary = execSummaryMatch[1].trim();
            return summary.length > 200 ? summary.substring(0, 200) + "..." : summary;
          }
        }
        return "暂无摘要信息";
      })(),
      breakdown: (() => {
        try {
          if (testData.graphdata) {
            let graphdata = typeof testData.graphdata === 'string' 
              ? JSON.parse(testData.graphdata) 
              : testData.graphdata;
            
            return Object.entries(graphdata)
              .filter(([key]) => key !== 'overall_greenwashing_score')
              .map(([key, value]: [string, any]) => ({
                type: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                value: Math.round((value?.score ?? 0) * 10) // 转换为 0-100 范围
              }));
          }
          return [];
        } catch (e) {
          console.error('Failed to parse test breakdown data:', e);
          return [];
        }
      })(),
      evidenceGroups: (() => {
        try {
          const docAnalysis = testData.document_analysis;
          if (Array.isArray(docAnalysis) && docAnalysis.length > 0) {
            const analysisItems = Array.isArray(docAnalysis[0]) ? docAnalysis[0] : docAnalysis;
            const validItems = analysisItems.filter((item: any) => 
              item && (item.quotation || item.quote) && (item.explanation || item.why)
            );
            
            if (validItems.length > 0) {
              return validItems.map((item: any) => ({
                type: "关键声明",
                items: [{
                  quote: item.quotation || item.quote || "",
                  why: item.explanation || item.why || ""
                }]
              }));
            }
          }
        } catch (e) {
          console.error('Failed to parse test evidence data:', e);
        }
        return [];
      })(),
      external: (() => {
        const external = [];
        
        if (testData.news_validation && testData.news_validation.trim()) {
          const newsText = testData.news_validation.substring(0, 200);
          if (newsText.length === 200) {
            external.push(newsText + "...");
          } else {
            external.push(newsText);
          }
        }
        
        if (testData.wikirate_validation && testData.wikirate_validation.trim()) {
          const wikiText = testData.wikirate_validation.substring(0, 200);
          if (wikiText.length === 200) {
            external.push(wikiText + "...");
          } else {
            external.push(wikiText);
          }
        }
        
        if (external.length === 0) {
          external.push("暂无外部验证数据");
        }
        
        return external;
      })(),
    };

    // 使用测试数据覆盖 view
    Object.assign(view, testView);
    console.log('🔧 测试数据已应用:', testView);
  }
const safeBreakdown = Array.isArray(view?.breakdown)
  ? view.breakdown.filter(
      (d: any) => d && typeof d.value === 'number' && !Number.isNaN(d.value)
    )
  : [];

return (
  <div className="min-h-screen [background-image:var(--gradient-soft)]">
    <Seo
      title={`${view.name} | ${t('company.title')}`}
      description={`${t('dashboard.riskScore')} ${view.score}, ${view.summary}`}
      canonical={typeof window !== 'undefined' ? window.location.href : undefined}
    />
    <TopNav />
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">{t('company.title')}</h1>
        <p className="text-muted-foreground mt-1">{t('company.subtitle')}</p>
      </header>

      {/* Risk & Breakdown */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t('company.overallRisk')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="relative">
                <div className="h-28 w-28 rounded-full grid place-items-center border-2"
                     style={{ borderColor: "hsl(var(--accent))", boxShadow: "var(--shadow-glow)" }}>
                  <span className="text-3xl font-bold">{view.score}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{t('company.riskLevel')}</span>
                  <Badge variant={riskTone(view.score) as any}>
                    {(() => {
                      if (view.score >= 70) return t('company.high');
                      if (view.score >= 40) return t('company.medium');
                      return t('company.low');
                    })()}
                  </Badge>
                </div>
                <div className="mt-2 leading-relaxed">
                  {view.summary ? <p>{view.summary}</p> : <p className="text-muted-foreground">暂无摘要信息</p>}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button asChild><a href="#evidence">{t('company.viewEvidence')}</a></Button>
                  <Button variant="secondary" asChild><a href="#actions">{t('company.nextSteps')}</a></Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>1.Risk Type Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {safeBreakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={safeBreakdown} outerRadius={80}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="type" />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} />
                  <Tooltip />
                  <Radar
                    name="风险"
                    dataKey="value"
                    stroke="hsl(var(--accent))"
                    fill="hsl(var(--accent))"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full grid place-items-center text-sm text-muted-foreground">
                暂无可视化数据（等待分析或数据不足）
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Evidence / External / Actions */}
      <section id="evidence" className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Evidence Chain */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>2.Key Findings and Evidence from Document Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            {Array.isArray(view?.evidenceGroups) && view.evidenceGroups.length > 0 ? (
              <div className="whitespace-pre-line">{view.evidenceGroups[0].items[0].quote}</div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>暂无报告内容</p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {/* External Verification */}
          <Card>
            <CardHeader>
              <CardTitle>3.Specific Recommendations for Stakeholders</CardTitle>
            </CardHeader>
            <CardContent>
              {Array.isArray(view?.external) && view.external.length > 0 ? (
                <div className="whitespace-pre-line">{view.external[0]}</div>
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  <p>暂无报告内容</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recommended Steps */}
          <Card id="actions">
            <CardHeader>
              <CardTitle>4.Risk Assessment and Concerns</CardTitle>
            </CardHeader>
            <CardContent>
              {view.recommendedSteps ? (
                <div className="whitespace-pre-line">{view.recommendedSteps}</div>
              ) : (
                <p>暂无建议</p>
              )}
              <div className="mt-4 flex gap-2">
                <Button asChild><Link to="/upload">{t('company.addReports')}</Link></Button>
                <Button variant="secondary">{t('company.exportPdf')}</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
    <FloatingChatbot />
  </div>
);

}
export default Company;
