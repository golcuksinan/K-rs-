import {
Navigate
} from "react-router-dom";


import {
useContext
} from "react";


import {
AuthContext
} from "../context/auth-context";


export default function ProtectedRoute({children}){


const {
user,
loading
}=useContext(AuthContext);



if(loading){

return (

<div className="p-20 text-center">

Yükleniyor...

</div>

)

}



if(!user){

return (

<Navigate to="/giris"/>

)

}



return children;


}