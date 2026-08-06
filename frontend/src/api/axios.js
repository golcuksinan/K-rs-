import axios from "axios";


const api = axios.create({

    // Boşsa vite'ın (prod'da nginx'in) /api proxy'si kullanılır; sayfayla aynı
    // origin'e gidildiği için hem localhost'tan hem telefondan çalışır.
    baseURL: import.meta.env.VITE_API_URL || "/api",

    headers:{
        "Content-Type":"application/json"
    }

});


api.interceptors.request.use((config)=>{

    const token = localStorage.getItem("token");

    if(token){

        config.headers.Authorization = `Bearer ${token}`;

    }

    return config;

});


// Şifre sıfırlaması eski token'ları geçersizleştiriyor; elde kalan token'la gezilmesin.
// /auth/* 401'leri hatalı giriş demek, oturum düşmesi değil.
api.interceptors.response.use(

    (response)=>response,

    (error)=>{

        const istekAuth = error.config?.url?.startsWith("/auth/");

        if(error.response?.status === 401 && !istekAuth && localStorage.getItem("token")){

            localStorage.removeItem("token");

            if(window.location.pathname !== "/giris"){

                window.location.assign("/giris");

            }

        }

        return Promise.reject(error);

    }

);


export default api;
