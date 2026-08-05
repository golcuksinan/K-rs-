import { useContext, useState } from "react";

import { createReport } from "../api/reports";

import parseError from "../api/parseError";

import { AuthContext } from "../context/auth-context";

import Card from "./Card";
import ErrorMessage from "./Error";
import Rating from "./Rating";


const MIN_GEREKCE = 3;

const MAX_GEREKCE = 500;


export default function ReviewCard({ review, etiket }) {

    const { user } = useContext(AuthContext);

    const [acik, setAcik] = useState(false);

    const [gerekce, setGerekce] = useState("");

    const [hata, setHata] = useState("");

    const [bildirildi, setBildirildi] = useState(false);


    const bildir = (e) => {

        e.preventDefault();

        setHata("");

        createReport({ review_id: review.id, reason: gerekce.trim() })

            .then(() => {

                setBildirildi(true);

                setAcik(false);

            })

            .catch((error) => setHata(parseError(error)));

    };


    return (

        <Card className="p-6">

            {etiket && (

                <p className="text-sm text-gray-600 mb-3">

                    {etiket}

                </p>

            )}

            <Rating
                teaching={review.teaching_score}
                difficulty={review.difficulty_score}
                fairness={review.fairness_score}
            />

            {review.comment && (

                <p className="mt-4 whitespace-pre-line">

                    {review.comment}

                </p>

            )}

            <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">

                <span>

                    {new Date(review.created_at).toLocaleDateString("tr-TR")}

                </span>

                {user && !bildirildi && (

                    <button className="underline" onClick={() => setAcik(!acik)}>

                        Bildir

                    </button>

                )}

                {bildirildi && <span>Bildiriminiz alındı</span>}

            </div>

            {acik && (

                <form onSubmit={bildir} className="mt-4 space-y-3">

                    <textarea
                        className="w-full border p-3 h-20"
                        placeholder="Neden bildiriyorsunuz?"
                        minLength={MIN_GEREKCE}
                        maxLength={MAX_GEREKCE}
                        value={gerekce}
                        onChange={(e) => setGerekce(e.target.value)}
                    />

                    <button className="bg-[#102744] text-white px-6 py-2 text-sm">

                        Gönder

                    </button>

                </form>

            )}

            <ErrorMessage message={hata} />

        </Card>

    );

}
