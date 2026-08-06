// Liste uçlarının Page zarfı; testler yalnızca items/total okuyor.
export const sayfa = (items) =>
    Promise.resolve({ data: { items, total: items.length, limit: 50, offset: 0 } });
