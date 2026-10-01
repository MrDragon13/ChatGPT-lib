import { describe, expect, it } from "vitest";

import type { WebManifest, WebWork } from "../../data/types";
import {
  filterLibrary,
  libraryFiltersFromSearchParams,
  libraryFiltersToSearchParams,
  type LibraryFilters,
} from "./selectors";

function work(
  id: string,
  titleRu: string,
  titleOriginal: string,
  year: number,
  genres: string[],
  primaryStatus: string,
  partnerStatus: string,
  alternateTitles: string[] = [],
): WebWork {
  return {
    id,
    identity: { title_ru: titleRu, title_original: titleOriginal, alternate_titles: alternateTitles, year },
    metadata: { external: { genres, runtime_min: 120 } },
    viewer_signals: {
      primary: { viewing: { status: primaryStatus } },
      partner: { viewing: { status: partnerStatus } },
    },
    group_signals: {},
    interest: {},
    traits: [],
    collections: [],
    provenance: { created_at: null, updated_at: null },
  };
}

function manifest(): WebManifest {
  return {
    schema_version: 1,
    default_target: "couple",
    targets: { viewers: ["primary", "partner"], groups: { couple: ["primary", "partner"] } },
    vocabulary: {
      "genre.science_fiction": { kind: "genre", label_ru: "Фантастика" },
      "genre.drama": { kind: "genre", label_ru: "Драма" },
    },
    profiles: {},
    recommendations: {},
    works: [
      work(
        "arrival-2016",
        "Прибытие",
        "Arrival",
        2016,
        ["genre.science_fiction", "genre.drama"],
        "watched",
        "unwatched",
        ["Story of Your Life"],
      ),
      work("dune-2021", "Дюна", "Dune", 2021, ["genre.science_fiction"], "unwatched", "watched"),
      work("drama-2016", "Тихая драма", "Quiet Drama", 2016, ["genre.drama"], "unwatched", "unwatched"),
    ],
  };
}

const all: LibraryFilters = { query: "", viewing: "all", genre: null, year: null };

describe("library filters", () => {
  it("searches Russian, original and alternate titles case-insensitively", () => {
    const data = manifest();
    expect(filterLibrary(data, "primary", { ...all, query: "прибыт" }).map((item) => item.id)).toEqual(["arrival-2016"]);
    expect(filterLibrary(data, "primary", { ...all, query: "ARRIVAL" }).map((item) => item.id)).toEqual(["arrival-2016"]);
    expect(filterLibrary(data, "primary", { ...all, query: "story of your life" }).map((item) => item.id)).toEqual(["arrival-2016"]);
  });

  it("applies viewing status to the selected viewer instead of globally", () => {
    const data = manifest();
    expect(filterLibrary(data, "primary", { ...all, viewing: "watched" }).map((item) => item.id)).toEqual(["arrival-2016"]);
    expect(filterLibrary(data, "partner", { ...all, viewing: "watched" }).map((item) => item.id)).toEqual(["dune-2021"]);
    expect(filterLibrary(data, "partner", { ...all, viewing: "unwatched" }).map((item) => item.id)).toEqual([
      "arrival-2016",
      "drama-2016",
    ]);
  });

  it("composes genre and year filters", () => {
    const data = manifest();
    expect(
      filterLibrary(data, "primary", {
        ...all,
        genre: "genre.drama",
        year: 2016,
      }).map((item) => item.id),
    ).toEqual(["arrival-2016", "drama-2016"]);
  });

  it("round-trips filters and target through URL search params", () => {
    const filters: LibraryFilters = {
      query: "дюна",
      viewing: "unwatched",
      genre: "genre.science_fiction",
      year: 2021,
    };
    const params = libraryFiltersToSearchParams(filters, "partner");
    expect(params.get("target")).toBe("partner");
    expect(libraryFiltersFromSearchParams(params)).toEqual(filters);
  });
});
