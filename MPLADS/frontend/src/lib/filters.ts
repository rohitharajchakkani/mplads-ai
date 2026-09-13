import type { Filters } from "../api/types";

const filterKeys: Array<keyof Filters> = ["house", "state", "district_or_ida", "mp", "work", "constituency", "financial_year", "work_status"];

export function filtersFromSearch(search: URLSearchParams): Filters {
  return filterKeys.reduce<Filters>((filters, key) => {
    const value = search.get(key);
    if (value) filters[key] = value;
    return filters;
  }, {});
}

export function queryFromFilters(filters: Filters): URLSearchParams {
  const search = new URLSearchParams();
  for (const key of filterKeys) if (filters[key]) search.set(key, filters[key]);
  return search;
}

export const filterLabels: Record<keyof Filters, string> = {
  house: "House",
  state: "State",
  district_or_ida: "District / IDA",
  mp: "MP",
  work: "Work",
  constituency: "Constituency",
  financial_year: "Financial year",
  work_status: "Source work status",
};
