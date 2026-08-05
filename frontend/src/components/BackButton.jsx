import { useNavigate } from "react-router-dom";


export default function BackButton() {

    const navigate = useNavigate();

    return (

        <button className="underline cursor-pointer" onClick={() => navigate(-1)}>

            ← Geri

        </button>

    );

}
