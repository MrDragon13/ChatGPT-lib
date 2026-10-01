import "@testing-library/jest-dom/vitest";

class TestIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "0px";
  readonly thresholds = [0];

  disconnect() {}
  observe(target: Element) {
    this.callback(
      [
        {
          boundingClientRect: target.getBoundingClientRect(),
          intersectionRatio: 1,
          intersectionRect: target.getBoundingClientRect(),
          isIntersecting: true,
          rootBounds: null,
          target,
          time: 0,
        },
      ],
      this,
    );
  }
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
  unobserve() {}

  constructor(private readonly callback: IntersectionObserverCallback) {}
}

vi.stubGlobal("IntersectionObserver", TestIntersectionObserver);
