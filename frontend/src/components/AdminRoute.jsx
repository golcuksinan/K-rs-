import { useContext } from "react";

import { Navigate } from "react-router-dom";

import { AuthContext } from "../context/auth-context";


export default function AdminRoute({ children }) {

    const { user, loading } = useContext(AuthContext);

    if (loading) {

        return (

            <div className="p-20 text-center">

                Yükleniyor...

            </div>

        );

    }

    if (!user) {

        return <Navigate to="/giris" />;

    }

    // Admin uçları zaten 403 döner; bağlantıyı bilen normal kullanıcıya boş ekran gösterilmez.
    if (user.role !== "admin") {

        return <Navigate to="/" replace />;

    }

    return children;

}
