export default function Pagination({ total, limit, offset, onChange }) {

    if (total <= limit) {

        return null;

    }

    const sayfa = Math.floor(offset / limit) + 1;

    const sonSayfa = Math.ceil(total / limit);

    return (

        <div className="flex items-center justify-center gap-4 mt-10">

            <button
                className="border border-[#102744] px-4 py-2 disabled:opacity-40"
                disabled={offset === 0}
                onClick={() => onChange(Math.max(offset - limit, 0))}
            >

                Önceki

            </button>

            <span className="text-sm">

                {sayfa} / {sonSayfa}

            </span>

            <button
                className="border border-[#102744] px-4 py-2 disabled:opacity-40"
                disabled={offset + limit >= total}
                onClick={() => onChange(offset + limit)}
            >

                Sonraki

            </button>

        </div>

    );

}
