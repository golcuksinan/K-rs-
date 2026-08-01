import {
useState
} from "react";

import {
createReview
} from "../../api/reviews";


export default function CreateReview(){


const [form,setForm]=useState({

rating:5,
comment:""

});



const submit=(e)=>{

e.preventDefault();


createReview(form)

.then(()=>{

alert("Yorum gönderildi");

});


};



return (

<section className="
max-w-xl
mx-auto
px-6
py-16
">


<h1 className="
heading-font
text-4xl
mb-8
">

Yorum Yap

</h1>



<form

onSubmit={submit}

className="
space-y-5
"

>


<input

type="number"

min="1"

max="5"

value={form.rating}

onChange={(e)=>

setForm({

...form,

rating:e.target.value

})

}

className="
w-full
border
p-3
"

/>



<textarea

value={form.comment}

onChange={(e)=>

setForm({

...form,

comment:e.target.value

})

}

className="
w-full
border
p-3
h-32
"

/>



<button

className="
bg-[#102744]
text-white
px-8
py-3
"

>

Gönder

</button>


</form>


</section>

);

}