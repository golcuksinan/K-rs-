export default function ErrorMessage({ message }) {

    if (!message) {

        return null;

    }

    return (

        <div className="text-center py-10 text-red-600">

            {message}

        </div>

    );

}
