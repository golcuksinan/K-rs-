// Tek skor yok: anlatım/zorluk/adalet ayrı ortalamalar. Ortalamalar yalnızca onaylı
// yorumlardan hesaplandığı için hiç onaylı yorum yokken üçü de null gelir.
export default function Rating({ teaching, difficulty, fairness }) {

    if (teaching === null || teaching === undefined) {

        return (

            <p className="text-sm text-gray-600">

                henüz yorum yok

            </p>

        );

    }

    return (

        <dl className="flex gap-6 text-sm">

            {[

                ["Anlatım", teaching],

                ["Zorluk", difficulty],

                ["Adalet", fairness],

            ].map(([etiket, deger]) => (

                <div key={etiket}>

                    <dt className="text-gray-600">

                        {etiket}

                    </dt>

                    <dd className="font-semibold">

                        {deger?.toFixed(1)} / 5

                    </dd>

                </div>

            ))}

        </dl>

    );

}
