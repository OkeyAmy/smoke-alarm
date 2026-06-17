// Labeled fixtures for the smoke-alarm classifier self-test.
// Each test title encodes its expected category: ..._expect_<CAT>.

function add(a: number, b: number): number {
  return a + b;
}

describe('add', () => {
  it('value equality expect_S1', () => {
    expect(add(2, 3)).toBe(5);
  });

  it('error check expect_S2', () => {
    expect(() => {
      throw new Error('boom');
    }).toThrow();
  });

  it('strong combo expect_S3', () => {
    expect(add(2, 2)).toBe(4);
    expect(() => JSON.parse('{')).toThrow();
  });

  it('no assertion expect_W1', () => {
    const result = add(1, 1);
    console.log(result);
  });

  it('defined only expect_W2', () => {
    expect(add(1, 1)).toBeDefined();
  });

  it('mock only expect_W4', () => {
    const spy = jest.fn();
    spy();
    expect(spy).toHaveBeenCalled();
  });

  it('snapshot only expect_W5', () => {
    expect(add(1, 2)).toMatchSnapshot();
  });
});
