export interface ArticleSource {
  type: "article";
  title: string;
  url: string;
  label: string;
}

export interface FundFactSheetSource {
  type: "fund_fact_sheet";
  title: string;
  url: null;
  label: string;
}

export type Source = ArticleSource | FundFactSheetSource;
