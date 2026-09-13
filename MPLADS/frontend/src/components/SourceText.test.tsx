import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceText } from "./SourceText";

describe("SourceText component", () => {
  it("renders valid Unicode and English text normally without alterations", () => {
    render(<SourceText text="Construction of Community Hall at Ward 12" />);
    expect(screen.getByText("Construction of Community Hall at Ward 12")).toBeInTheDocument();
  });

  it("renders valid multilingual Unicode text normally", () => {
    render(<SourceText text="सामुदायिक भवन निर्माण" />);
    expect(screen.getByText("सामुदायिक भवन निर्माण")).toBeInTheDocument();
  });

  it("replaces heavily corrupted question mark sequences with a compact indicator instead of blocks of ???", () => {
    render(<SourceText text="???????????????????????????????????????" />);
    expect(screen.getByText(/Source text unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Source encoding issue in portal dataset/i)).toBeInTheDocument();
    expect(screen.queryByText(/\?{5,}/)).toBeNull();
  });

  it("replaces replacement character sequences with a compact indicator", () => {
    render(<SourceText text="\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD\uFFFD" />);
    expect(screen.getByText(/Source text unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Source encoding issue in portal dataset/i)).toBeInTheDocument();
  });

  it("handles isolated corrupted blocks inline while preserving surrounding valid words", () => {
    render(<SourceText text="Installation of solar lights at ??????? Gram Panchayat" />);
    expect(screen.getByText(/Installation of solar lights at/)).toBeInTheDocument();
    expect(screen.getByText(/Gram Panchayat/)).toBeInTheDocument();
    expect(screen.getByText("[Source encoding issue]")).toBeInTheDocument();
  });

  it("renders graceful fallback when text is null or empty", () => {
    render(<SourceText text={null} />);
    expect(screen.getByText(/Description not available in source record/i)).toBeInTheDocument();
  });
});
